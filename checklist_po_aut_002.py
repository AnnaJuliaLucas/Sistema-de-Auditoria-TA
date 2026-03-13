# checklist_po_aut_002.py
# Conteúdo extraído LITERALMENTE do documento "Checklist de Auditoria.docx"
# PO.AUT.002 Rev3 | Guia do Auditor | 30/05/2025
# Aprovadores: Viktor Eduardo Abu Kamel | Carolina Miller
#
# Estrutura de cada entrada:
#   'verificar'  : list[str]  — itens da coluna "O que verificar" (uma string por bullet)
#   'regras'     : list[str]  — itens da coluna "Regras Especiais"
#   'nota4'      : str        — texto da coluna "Critério Nota 4"
#   'armadilhas' : list[str]  — itens da coluna "Armadilhas"
#   'hard_rule'  : str|None   — regra rígida que gera nota 0 automática

CHECKLIST = {

    # =========================================================
    # PRÁTICA 1 — ROTINAS DE TA  (PS 0005)
    # =========================================================

    (1, 0): {   # 1.1 Backup Periódico e por Evento
        'verificar': [
            'Ordens SAP (3 últimas)',
            'VersionDog (ano corrente)',
            'Cobertura: PLCs, Supervisórios, Drives',
        ],
        'regras': [
            '⚠ HD Externo: Máx nota 3',
            '⚠ Jobs com erro: NC',
        ],
        'nota4': 'Backup de TODOS via SAP Cíclico ou VersionDog sem erros.',
        'armadilhas': [
            'Esquecer drives e supervisórios.',
            'Apenas CLPs não basta.',
        ],
        'hard_rule': None,
    },

    (1, 1): {   # 1.2 Redundância e Organização
        'verificar': [
            'Organização por data',
            '2 locais distintos',
            'Servidor redundante',
        ],
        'regras': [
            '⚠ HD Externo: Máx nota 3',
        ],
        'nota4': '2 locais ou RAID + SAP Cíclico ou VersionDog.',
        'armadilhas': [
            'Cópia única em máquina local.',
        ],
        'hard_rule': None,
    },

    (1, 2): {   # 1.3 Teste de Backup
        'verificar': [
            '3 ordens SAP',
            'Texto: passo a passo, fonte, data',
            'Print do restore',
        ],
        'regras': [
            '⚠ Sem texto descritivo na ordem = NC',
        ],
        'nota4': 'Testes TRIMESTRAIS em TODOS via SAP com procedimento.',
        'armadilhas': [
            'Ordem SAP vazia ou genérica ("Teste OK").',
        ],
        'hard_rule': None,
    },

    (1, 3): {   # 1.4 Controle de Modificações
        'verificar': [
            'Ordens SAP',
            'Histórico VersionDog',
            'Login pessoal',
        ],
        'regras': [
            '⚠ Só CLPs = Insuficiente',
        ],
        'nota4': 'TODAS alterações registradas com login pessoal/VersionDog.',
        'armadilhas': [
            'Não evidenciar controle em supervisórios.',
        ],
        'hard_rule': None,
    },

    (1, 4): {   # 1.5 Falhas e Alarmes
        'verificar': [
            '3 ordens SAP',
            'Procedimento detalhado',
        ],
        'regras': [
            '⚠ Confundir com rede = NC',
        ],
        'nota4': 'Rota de inspeção cíclica (PDM) no SAP detalhada.',
        'armadilhas': [
            'Apresentar relatório de rede ao invés de alarmes.',
        ],
        'hard_rule': None,
    },

    (1, 5): {   # 1.6 Verificação de Redes
        'verificar': [
            'Relatório técnico',
            'Ethernet: 2 ordens',
            'Profibus: 3 ordens',
        ],
        'regras': [
            '⚠ Ethernet: periodicidade 2 anos',
            '⚠ Profibus: periodicidade 1 ano',
        ],
        'nota4': 'Certificação periódica padrão + histórico SAP.',
        'armadilhas': [
            'Relatórios vencidos (fora da periodicidade).',
        ],
        'hard_rule': None,
    },

    (1, 6): {   # 1.7 Manutenção Preventiva
        'verificar': [
            '3 ordens SAP',
            'CLPs',
        ],
        'regras': [
            '⚠ Só CLP = Suficiente (drives e supervisórios não são avaliados aqui)',
        ],
        'nota4': 'PDM cíclico cobrindo todo o hardware.',
        'armadilhas': [
            'Preventiva sem registro no SAP (apenas planilha).',
        ],
        'hard_rule': None,
    },

    (1, 7): {   # 1.8 KPI Indisponibilidade
        'verificar': [
            'KPI ARMP separado',
            'Meta definida',
            'Ano corrente',
        ],
        'regras': [
            '🚨 REGRA HARD: KPI misturado ou ano anterior = Nota 0',
        ],
        'nota4': 'KPI identificado + 100% da meta atingida.',
        'armadilhas': [
            'KPI "Manutenção" geral sem separar Automação.',
        ],
        'hard_rule': 'KPI misturado com outras áreas OU referente a ano anterior = NOTA 0 AUTOMÁTICA',
    },

    # =========================================================
    # PRÁTICA 2 — SOBRESSALENTES  (PS 0006)
    # =========================================================

    (2, 0): {   # 2.1 Verificação de Sobressalentes
        'verificar': [
            '3 ordens SAP',
            'Conferência in loco',
            'Teste a quente (críticos)',
        ],
        'regras': [
            '⚠ Sem avaliar estoque = NC',
        ],
        'nota4': 'Inspeção + Teste a quente + Avaliação estoque + SAP.',
        'armadilhas': [
            'Não realizar testes a quente em itens críticos.',
        ],
        'hard_rule': None,
    },

    (2, 1): {   # 2.2 Equipamentos c/ Sobressalente
        'verificar': [
            'Lista/Planilha',
            'Fotos do estoque',
            'Doc. SIG (critérios)',
        ],
        'regras': [
            '⚠ Doc. SIG obrigatório para nota 4',
        ],
        'nota4': 'Críticos c/ estoque + Metodologia no SIG.',
        'armadilhas': [
            'Falta de documento formal definindo quantidades mínimas.',
        ],
        'hard_rule': None,
    },

    # =========================================================
    # PRÁTICA 3 — MAPA DE ATIVOS  (PS 0007)
    # =========================================================

    (3, 0): {   # 3.1 Hardware (Power BI)
        'verificar': [
            'Planilha completa',
            'Campos obrigatórios preenchidos',
            '3 ordens de atualização',
        ],
        'regras': [
            '⚠ Campos vazios = Redução de nota',
        ],
        'nota4': 'Planilha completa + Atualização sistemática + SAP anual.',
        'armadilhas': [
            'Campos "Criticidade" ou "Código Sobressalente" vazios.',
        ],
        'hard_rule': None,
    },

    (3, 1): {   # 3.2 Software (Power BI)
        'verificar': [
            'IP, SO, Patch, Versão',
            'Licenças',
            '3 ordens de atualização',
        ],
        'regras': [
            '⚠ IP/SO/Patch são campos críticos',
        ],
        'nota4': 'Planilha completa + VersionDog + SAP anual.',
        'armadilhas': [
            'Não preencher IP ou nível de Patch de segurança.',
        ],
        'hard_rule': None,
    },

    # =========================================================
    # PRÁTICA 4 — DISSEMINAÇÃO DO CONHECIMENTO  (PS 0008)
    # =========================================================

    (4, 0): {   # 4.1 Treinamentos Equipe
        'verificar': [
            'Mapa por cargo',
            'Cronograma',
            'Certificados',
        ],
        'regras': [],
        'nota4': 'Mapa + Cronograma EM DIA + Rotina de atualização.',
        'armadilhas': [
            'Cronograma existe mas está atrasado.',
        ],
        'hard_rule': None,
    },

    (4, 1): {   # 4.2 Treinamentos Responsáveis
        'verificar': [
            'Mapeamento completo',
            'Certificados',
        ],
        'regras': [],
        'nota4': 'Todos mapeados + Cronograma EM DIA.',
        'armadilhas': [
            'Mapear apenas treinamentos básicos.',
        ],
        'hard_rule': None,
    },

    (4, 2): {   # 4.3 Boas Práticas
        'verificar': [
            'Ata / Lista de presença',
            'Apresentação',
        ],
        'regras': [
            '⚠ % de participação exigida',
        ],
        'nota4': 'Sistematizada todas as áreas + >80% de participação.',
        'armadilhas': [
            'Apresentar apenas para a própria equipe.',
        ],
        'hard_rule': None,
    },

    # =========================================================
    # PRÁTICA 5 — GESTÃO DE INFRAESTRUTURA  (PS 0009)
    # =========================================================

    (5, 0): {   # 5.1 Nobreak
        'verificar': [
            '3 ordens SAP',
            'Cobertura de críticos',
        ],
        'regras': [],
        'nota4': 'Todos críticos + Teste FORMAL no SAP (PDM).',
        'armadilhas': [
            'Testes informais sem registro.',
        ],
        'hard_rule': None,
    },

    (5, 1): {   # 5.2 Lista de IPs e IO
        'verificar': [
            'Excel/PDF',
            '3 ordens de atualização',
        ],
        'regras': [],
        'nota4': 'Ambas atualizadas + Verificação SAP/VersionDog.',
        'armadilhas': [
            'Falta lista de IO (só tem IP).',
        ],
        'hard_rule': None,
    },

    (5, 2): {   # 5.3 Diagramas
        'verificar': [
            'Físico (Papel)',
            'Digital',
        ],
        'regras': [],
        'nota4': 'Papel + Digital atualizados + MERIDIAN.',
        'armadilhas': [
            'Digital desatualizado em relação ao papel.',
        ],
        'hard_rule': None,
    },

    (5, 3): {   # 5.4 Ciclo de Vida
        'verificar': [
            'Matriz fim de vida',
            'Matriz risco',
        ],
        'regras': [],
        'nota4': 'Todos na matriz risco + Estratégia de troca definida.',
        'armadilhas': [
            'Saber que é obsoleto mas não ter plano de troca.',
        ],
        'hard_rule': None,
    },

    # =========================================================
    # PRÁTICA 6 — GESTÃO DE RISCOS  (PS 0010)
    # =========================================================

    (6, 0): {   # 6.1 Identificação de Riscos
        'verificar': [
            'Matriz de risco',
            '3 ordens SAP',
        ],
        'regras': [],
        'nota4': 'Todos mapeados + Atualização SEMESTRAL (SAP).',
        'armadilhas': [
            'Atualização apenas reativa (por evento).',
        ],
        'hard_rule': None,
    },

    (6, 1): {   # 6.2 Planos de Contingência
        'verificar': [
            'Telefones de contato',
            'Tempo de impacto',
            '3 ordens SAP',
        ],
        'regras': [],
        'nota4': 'Todos os riscos + Contatos/Impacto + Atualização Semestral.',
        'armadilhas': [
            'Planos sem telefones ou estimativa de impacto.',
        ],
        'hard_rule': None,
    },

    # =========================================================
    # PRÁTICA 7 — INTERFACE COM A TI  (PS 0011)
    # =========================================================

    (7, 0): {   # 7.1 Fronteiras de Responsabilidade
        'verificar': [
            'Documento formal',
            'Cobertura total',
        ],
        'regras': [],
        'nota4': 'Formal (SIG) para todos + Atualização por eventos.',
        'armadilhas': [
            'Acordo apenas verbal/informal.',
        ],
        'hard_rule': None,
    },

    (7, 1): {   # 7.2 Projetos Integrados
        'verificar': [
            'Treinamento',
            'Logs de falha',
            'Se N/A: Justificativa formal',
        ],
        'regras': [],
        'nota4': 'Treinamento formal + Logs + Docs no SAP/SIG.',
        'armadilhas': [
            'N/A sem registro formal do motivo.',
        ],
        'hard_rule': None,
    },

    # =========================================================
    # PRÁTICA 8 — RECURSOS DE SOFTWARE E HARDWARE  (PS 0012)
    # =========================================================

    (8, 0): {   # 8.1 Eng. Clients e IHM
        'verificar': [
            'Qtd mínima (2)',
            'Suporte SO (Obsolescência)',
        ],
        'regras': [],
        'nota4': 'Não obsoletos + Rotina de troca OU Hot-standby.',
        'armadilhas': [
            'Windows sem suporte (ex: Win 7).',
        ],
        'hard_rule': None,
    },

    (8, 1): {   # 8.2 Servidores
        'verificar': [
            'RAID (HD)',
            'Fonte redundante',
            'Backup externo',
        ],
        'regras': [],
        'nota4': 'Redundância Total + Backup Local Distinto + Não obsoleto.',
        'armadilhas': [
            'Redundância apenas de disco (falta fonte).',
        ],
        'hard_rule': None,
    },

    (8, 2): {   # 8.3 Teste Redundância
        'verificar': [
            'Ordens SAP',
            'Simulação de falha',
        ],
        'regras': [],
        'nota4': 'Periódicos + Simulação de falhas + Integrado SAP.',
        'armadilhas': [
            'Testes sem simulação real de falha.',
        ],
        'hard_rule': None,
    },

    (8, 3): {   # 8.4 Softwares
        'verificar': [
            'Licenças',
            'Suporte MS Ativo',
        ],
        'regras': [],
        'nota4': 'Licenciados + TODOS SOs com suporte ativo.',
        'armadilhas': [
            'Softwares antigos rodando em SO obsoleto.',
        ],
        'hard_rule': None,
    },

    # =========================================================
    # PRÁTICA 9 — CYBERSEGURANÇA  (PS 0015)
    # =========================================================

    (9, 0): {   # 9.1 Treinamento Cyber
        'verificar': [
            'Lista de participantes TA',
            'Lista de participantes Elétrica',
        ],
        'regras': [],
        'nota4': 'Ano atual 100% + Ano anterior >50%.',
        'armadilhas': [
            'Esquecer equipe elétrica.',
        ],
        'hard_rule': None,
    },

    (9, 1): {   # 9.2 Acesso Remoto
        'verificar': [
            'Ferramenta homologada?',
            'MFA ativo',
            'Logs de acesso',
        ],
        'regras': [
            '🚨 REGRA HARD: Não homologado = Nota 0',
        ],
        'nota4': 'Homologado + MFA + Logs + Firewall.',
        'armadilhas': [
            'TeamViewer/AnyDesk = Nota 0.',
        ],
        'hard_rule': 'Uso de ferramenta NÃO HOMOLOGADA (TeamViewer, AnyDesk, etc.) = NOTA 0 AUTOMÁTICA',
    },

    (9, 2): {   # 9.3 Backup Cyber
        'verificar': [
            'Doc. SIG',
            'Críticos listados',
        ],
        'regras': [],
        'nota4': 'Procedimento claro + Críticos + Teste de integridade.',
        'armadilhas': [
            'Não listar quais são os sistemas críticos.',
        ],
        'hard_rule': None,
    },

    (9, 3): {   # 9.4 Resposta a Incidentes
        'verificar': [
            'Doc. SIG',
            'RACI definida',
            'TI local acionada',
        ],
        'regras': [],
        'nota4': 'Procedimento + RACI + Acionamento TI.',
        'armadilhas': [
            'Sem matriz RACI definida.',
        ],
        'hard_rule': None,
    },

    (9, 4): {   # 9.5 Atualização (Patch)
        'verificar': [
            'Política TI',
            'Antivírus',
        ],
        'regras': [],
        'nota4': 'Estação segura (TI) + Patches/AV em dia.',
        'armadilhas': [
            'Antivírus desconectado da gestão central.',
        ],
        'hard_rule': None,
    },

    (9, 5): {   # 9.6 Gestão de Acesso
        'verificar': [
            'Físico / Lógico',
            'Segregação de rede',
        ],
        'regras': [],
        'nota4': 'Controle Cyber + Firewall + Sem senhas padrão.',
        'armadilhas': [
            'Senhas padrão de fábrica (admin/admin).',
        ],
        'hard_rule': None,
    },

    (9, 6): {   # 9.7 Mídias Removíveis
        'verificar': [
            'Sala trancada',
            'Logs de uso',
        ],
        'regras': [],
        'nota4': 'Mecanismo digital c/ logs OU Sem uso de mídia.',
        'armadilhas': [
            'Sala trancada mas muitos têm a chave.',
        ],
        'hard_rule': 'Mídias disponíveis para qualquer usuário sem critério de acesso = NOTA 0 AUTOMÁTICA',
    },
}


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================

def get_checklist(pratica_num: int, subitem_idx: int) -> dict:
    """Retorna o checklist para uma prática e sub-item específicos."""
    return CHECKLIST.get((pratica_num, subitem_idx), {})
