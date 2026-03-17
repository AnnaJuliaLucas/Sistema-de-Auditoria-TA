# internal_analyzer.py
# Um agente híbrido offline para rodar análises qualitativas no backend.
# Integra Heurísticas, Critérios Oficiais e RAG Local.

import os
import re
from pathlib import Path
from datetime import datetime
from ai_analyzer import preparar_evidencias

try:
    from backend.db import buscar_contexto_relevante
    from criterios_oficiais import CRITERIOS, REGRAS_GERAIS, get_criterio
    _RECURSOS_COMPLETOS = True
except ImportError:
    _RECURSOS_COMPLETOS = False
    CRITERIOS = {}
    REGRAS_GERAIS = ""
    def buscar_contexto_relevante(q, limit=3): return ""
    def get_criterio(p, s): return {}

class InternalHeuristicAnalyzer:
    def __init__(self):
        self.provider = "interno"

    def _get_patterns(self, pratica_num: int, subitem_idx: int) -> list:
        """Retorna padrões regex baseados no subitem para busca técnica."""
        patterns = []
        # Padrões genéricos de auditoria
        patterns.append(re.compile(r"ordem|sap|manutenc|preventiva|corretiva|registros", re.I))
        patterns.append(re.compile(r"conforme|atende|evidenc|comprov", re.I))
        
        # Padrões específicos por prática (mapeamento detalhado)
        spec = {
            (1, 0): [r"vdog", r"octoplant", r"backup", r"plc", r"drives", r"periodico"],
            (1, 1): [r"redund", r"servidor", r"hd\s*externo", r"mídia", r"centraliz"],
            (1, 2): [r"teste", r"backup", r"trimestral", r"planilha", r"print"],
            (1, 7): [r"kpi", r"sig", r"meta", r"indisponib", r"desvio"],
            (2, 0): [r"estoque", r"almoxarif", r"in\s*loco", r"confer", r"critico"],
            (3, 0): [r"planilha", r"hardware", r"sap", r"ip", r"pbi", r"power\s*bi"],
            (3, 1): [r"software", r"licenca", r"versao", r"vdog", r"arvore"],
            (4, 0): [r"treinamento", r"capacit", r"cronograma", r"certificado", r"lista", r"presenca"],
            (5, 0): [r"nobreak", r"ups", r"aliment", r"redund", r"pdm"],
            (5, 3): [r"ciclo\s*de\s*vida", r"matriz", r"risco", r"troca", r"obsoleto"],
            (9, 1): [r"firewall", r"vlan", r"segment", r"fortinet", r"cisco"],
            (9, 2): [r"vpn", r"acesso", r"remoto", r"homolog", r"tokens"]
        }
        
        p_list = spec.get((pratica_num, subitem_idx), [])
        for p in p_list:
            patterns.append(re.compile(p, re.I))
            
        return patterns

    def analyze_subitem(
        self,
        pratica_num: int,
        subitem_idx: int,
        pratica_nome: str,
        subitem_nome: str,
        evidencia_descricao: str,
        niveis_planilha: dict,
        nota_self_assessment: int,
        evidence_files: list
    ) -> dict:
        
        # 1. Preparar Evidências (Extração de Texto)
        evidencias_textuais, image_paths, relatorio_cobertura = preparar_evidencias(
            evidence_files,
            max_chars_total=150000,
            max_chars_pdf=15000,
            max_pages_pdf=15
        )

        total_files = len(evidence_files)
        full_text = " ".join([ev['conteudo'].lower() for ev in evidencias_textuais])
        
        # 2. Buscar Contexto Relevante (RAG)
        contexto_rag = buscar_contexto_relevante(f"{pratica_nome} {subitem_nome}")
        
        # 3. Obter Critérios Oficiais
        criterio = get_criterio(pratica_num, subitem_idx)
        niveis_oficiais = criterio.get("niveis", {})
        regras_especiais = criterio.get("regras_especiais", "")
        
        # 4. Análise Heurística de Rigor
        pontos_atendidos = []
        pontos_faltantes = []
        
        # 4.1. Verificação de Existência
        if total_files == 0:
            return self._format_result("inexistente", 0, "alta", [], ["Nenhuma evidência física anexada."], 
                                     "Falta total de comprovação.", relatorio_cobertura, "Nenhum arquivo encontrado na pasta de evidências.")

        # 4.2. Verificação de Padrões Técnicos (Match)
        patterns = self._get_patterns(pratica_num, subitem_idx)
        matches = [p.pattern for p in patterns if p.search(full_text)]
        match_ratio = len(matches) / len(patterns) if patterns else 1.0
        
        # 4.3. Verificação de Data (Simplificada: Procura por anos recentes)
        ano_atual = datetime.now().year
        tem_data_recente = any(str(ano_atual) in full_text or str(ano_atual-1) in full_text for ev in evidencias_textuais)
        
        # 4.4. Verificação de Falhas Específicas (Jobs com Erro, Incompleto)
        tem_erro_job = any(re.search(r"erro|fail|falha|abort|interrupt|warning", ev['conteudo'], re.I) for ev in evidencias_textuais if "vdog" in ev['conteudo'] or "backup" in ev['conteudo'])
        incompleto_evidencia = total_files < 2 or not any(re.search(r"print|screenshot|config|supervis", full_text, re.I))
        
        # 4.5. Busca por Decisões Passadas (Aprendizado)
        decisoes_passadas = ""
        if _RECURSOS_COMPLETOS:
            decisoes_hist = buscar_contexto_relevante(f"REF_DECISAO: Prática {pratica_num} Item {subitem_idx}", limit=2)
            if decisoes_hist:
                decisoes_passadas = f"\n**Experiência do Auditor (Histórico):**\n{decisoes_hist}\n"

        # 5. Lógica de Decisão Híbrida
        decisao = "insuficiente"
        nota_sugerida = 0
        confianca = "media"
        
        # Heurística de validação de nota
        if match_ratio >= 0.6 and tem_data_recente:
            decisao = "permanece"
            nota_sugerida = nota_self_assessment if nota_self_assessment is not None else 3
            pontos_atendidos.append(f"Identificados termos técnicos compatíveis: {', '.join(matches[:3])}")
            pontos_atendidos.append("Documentação apresenta referências a datas recentes.")
        elif total_files > 0:
            decisao = "insuficiente"
            nota_sugerida = max(0, (nota_self_assessment or 1) - 1)
            pontos_faltantes.append("A documentação anexada não contém termos técnicos obrigatórios ou referências a datas recentes.")
            if not tem_data_recente:
                pontos_faltantes.append("As evidências parecem ser antigas ou não datadas.")

        # 6. Construção da Justificativa e NC em 3 Pontos
        rag_combined = (contexto_rag + decisoes_passadas).strip()
        
        # Template de NC em 3 Pontos (Padrão Ouro solicitado pelo usuário)
        nc_padrão = ""
        if decisao != "permanece":
            ponto_1 = "1. Problema Detectado: "
            if tem_erro_job:
                ponto_1 += "Presença de erros/falhas detectada nos logs de Job ou backup, indicando que a rotina não é resiliente."
            elif not tem_data_recente:
                ponto_1 += "Ausência de evidências temporais recentes. Os documentos apresentados parecem ser antigos ou não datados."
            else:
                ponto_1 += "Desconexão técnica entre as evidências enviadas e os requisitos de maturidade do item."

            ponto_2 = "\n2. Evidências Incompletas: "
            if incompleto_evidencia:
                ponto_2 += "Os arquivos anexados mostram apenas parte da rotina (ex: apenas pastas ou registros parciais). Falta demonstrar a cobertura total dos equipamentos citados no critério."
            else:
                ponto_2 += "Faltam correlações claras (prints de sistemas, ordens SAP encerradas) que comprovem a execução sistêmica."

            ponto_3 = f"\n3. Conformidade com Critérios: Para alcançar o nível de conformidade adequado, é necessário demonstrar que {niveis_oficiais.get(3, 'a rotina é executada de forma plena e automática')}. {regras_especiais or 'Conforme diretrizes do PO.AUT.002.'}"
            nc_padrão = f"{ponto_1}\n{ponto_2}\n{ponto_3}"

        justificativa = (
            f"### PARECER TÉCNICO DE AUDITORIA\n\n"
            f"**Critério Oficial:** {criterio.get('descricao', subitem_nome)}\n"
            f"**Histórico e Contexto:** {rag_combined or 'Novo subitem sem histórico prévio.'}\n\n"
            f"**Análise de Evidências:**\n"
            f"- Arquivos: {total_files} ({len(evidencias_textuais)} docs, {len(image_paths)} imagens)\n"
            f"- Aderência Normativa: {match_ratio*100:.0f}%\n"
            f"- Validação Temporal: {'OK' if tem_data_recente else '⚠️ Pendente/Antiga'}\n"
            f"- Integridade de Jobs: {'❌ Falhas Detectadas' if tem_erro_job else '✅ Sem erros aparentes'}\n\n"
            f"**Conclusão:** {'A nota do Self-Assessment é validada pelo motor de regras.' if decisao == 'permanece' else 'Rebaixamento sugerido devido a gaps qualitativos na evidência.'}"
        )

        return self._format_result(decisao, nota_sugerida, confianca, pontos_atendidos, pontos_faltantes, 
                                 nc_padrão, relatorio_cobertura, justificativa, total_files, len(image_paths), len(evidencias_textuais))

    def _format_result(self, decisao, nota, confianca, atendidos, faltantes, nc, cobertura, detalhe, files=0, imgs=0, docs=0):
        # Limitar detalhe e NC para não estourar campos se necessário, mas manter estrutura
        return {
            "decisao": decisao,
            "nota_sugerida": nota,
            "confianca": confianca,
            "pontos_atendidos": atendidos,
            "pontos_faltantes": faltantes,
            "descricao_nc": nc,
            "comentarios": "Análise realizada pelo motor interno baseado em critérios oficiais e heurísticas de conformidade.",
            "analise_detalhada": detalhe,
            "arquivos_analisados": files,
            "imagens_analisadas": imgs,
            "docs_analisados": docs,
            "imgs_detalhe": "none",
            "criterios_source": "interno_hibrido",
            "cobertura_relatorio": cobertura
        }
