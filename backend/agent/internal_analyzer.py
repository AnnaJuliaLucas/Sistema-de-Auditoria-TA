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

        # 6. Construção da Justificativa Técnica
        rag_info = f"\n**Base de Conhecimento:** {contexto_rag[:300]}...\n" if contexto_rag else ""
        
        justificativa = (
            f"### ANÁLISE QUALITATIVA (SISTEMA INTERNO)\n\n"
            f"**Critério Oficial:** {criterio.get('descricao', subitem_nome)}\n"
            f"**Contexto Normativo:** {regras_especiais or 'Geral do PO.AUT.002'}\n"
            f"{rag_info}\n"
            f"**Arquivos Analisados:** {total_files} ({len(evidencias_textuais)} docs, {len(image_paths)} imagens)\n"
            f"**Aderência Técnica:** {match_ratio*100:.0f}% dos padrões identificados.\n"
            f"**Validação Temporal:** {'OK (Datas recentes encontradas)' if tem_data_recente else '⚠️ ALERTA (Nenhuma data recente detectada no texto)'}.\n\n"
            f"**Parecer:** A análise interna verificou os documentos contra os critérios de maturidade. "
            f"{'A nota declarada (' + str(nota_self_assessment) + ') é sustentada pela presença de termos específicos e evidências de rotina.' if decisao == 'permanece' else 'A evidência é considerada fraca ou desconexa para a nota ' + str(nota_self_assessment) + ' devido à falta de correlação direta com os requisitos mínimos de auditoria.'}"
        )

        return self._format_result(decisao, nota_sugerida, confianca, pontos_atendidos, pontos_faltantes, 
                                 "GAP técnico identificado na análise offline." if decisao != "permanece" else "", 
                                 relatorio_cobertura, justificativa, total_files, len(image_paths), len(evidencias_textuais))

    def _format_result(self, decisao, nota, confianca, atendidos, faltantes, nc, cobertura, detalhe, files=0, imgs=0, docs=0):
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
