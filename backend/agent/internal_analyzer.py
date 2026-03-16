# internal_analyzer.py
# Um agente heurístico offline (sem IA pesada) para rodar análises diretamente no backend.

import os
from pathlib import Path
from ai_analyzer import preparar_evidencias

class InternalHeuristicAnalyzer:
    def __init__(self):
        self.provider = "interno"

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
        
        # 1. Extrair evidências textuais da mesma forma que o agente tradicional
        evidencias_textuais, image_paths, relatorio_cobertura = preparar_evidencias(
            evidence_files,
            max_chars_total=100000,
            max_chars_pdf=10000,
            max_pages_pdf=10,
            max_chars_docx=10000,
            max_chars_xlsx=10000,
        )

        total_files = len(evidence_files)
        total_text = " ".join([ev['conteudo'].lower() for ev in evidencias_textuais])

        # Heurística Básica:
        # Se não enviou arquivo, nota 0
        if total_files == 0:
            return {
                "decisao": "inexistente",
                "nota_sugerida": 0,
                "confianca": "alta",
                "pontos_atendidos": [],
                "pontos_faltantes": ["Nenhum arquivo de evidência foi anexado."],
                "descricao_nc": "Falta total de comprovação.",
                "comentarios": "Por favor, anexe documentos comprobatórios ou fotos.",
                "analise_detalhada": "O Agente Interno (Heurístico) verificou que a pasta de evidências está vazia.",
                "arquivos_analisados": 0,
                "imgs_detalhe": "none",
                "criterios_source": "interno"
            }

        # Palavras-chave básicas baseadas no nome da prática e subitem
        keywords = set(subitem_nome.lower().split())
        keywords = {k.strip(".,()[]") for k in keywords if len(k) > 3}
        
        # Palavras exigidas genéricas de auditoria
        termos_positivos = {"relatório", "aprovado", "evidência", "conforme", "ok", "ativo", "sim", "backup", "log", "senha", "acesso"}
        
        pontos_atendidos = []
        pontos_faltantes = []
        match_count = sum(1 for kw in keywords if kw in total_text)
        
        if len(keywords) > 0:
            match_ratio = match_count / len(keywords)
        else:
            match_ratio = 1.0 if total_files > 0 else 0.0

        if match_ratio >= 0.5 or total_text.strip() != "":
            # Aceita se tiver boa cobertura ou se tiver algum conteúdo extraído
            decisao = "permanece"
            nota = nota_self_assessment if nota_self_assessment is not None else 4
            confianca = "media"
            pontos_atendidos.append(f"Documentação anexada contendo {len(evidencias_textuais)} texto(s) e {len(image_paths)} imagem(ns).")
            pontos_atendidos.append(f"Conteúdo extraído com sucesso, indícios de termos compatíveis com o subitem (Match: {match_count}/{len(keywords)}).")
            desc_nc = "Não conformidade não detectada pela heurística."
        else:
            # Se tem arquivos mas não extraiu nada ou não coincidiu minimamente
            decisao = "insuficiente"
            nota = max(0, (nota_self_assessment or 0) - 1)
            confianca = "baixa"
            pontos_faltantes.append("Os documentos anexados não parecem conter os termos chave descritos no subitem.")
            desc_nc = "Evidência parece não correlacionada com a descrição da prática requerida."

        detalhe = (
            f"Análise realizada pelo Agente Interno (Heurístico/Offline) — Sem LLM Externo.\n"
            f"Foram avaliados {total_files} arquivos.\n"
            f"Termos base da busca: {', '.join(keywords)}\n"
            f"Taxa de aderência heurística: {match_ratio*100:.1f}%\n"
            f"{relatorio_cobertura}"
        )

        return {
            "decisao": decisao,
            "nota_sugerida": nota,
            "confianca": confianca,
            "pontos_atendidos": pontos_atendidos,
            "pontos_faltantes": pontos_faltantes,
            "descricao_nc": desc_nc,
            "comentarios": "Obs: Esta análise foi gerada por um algoritmo local de correlação de texto, não por uma Inteligência Artificial.",
            "analise_detalhada": detalhe,
            "arquivos_analisados": total_files,
            "imagens_analisadas": len(image_paths),
            "docs_analisados": len(evidencias_textuais),
            "imgs_detalhe": "none",
            "criterios_source": "interno",
            "cobertura_relatorio": relatorio_cobertura
        }
