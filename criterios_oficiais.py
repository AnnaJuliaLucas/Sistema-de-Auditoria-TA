# criterios_oficiais.py
# Critérios extraídos LITERALMENTE do PO.AUT.002 – Procedimento de Auditoria TA Rev3
# Aprovado em: 30/05/2025
# VERSÃO 4.0 — reescrito com linguagem exata do documento oficial
#
# ESTRUTURA DO DOCUMENTO:
# A. PS 0005 – Rotinas de Tecnologia da Automação (8 sub-itens: 1.1 a 1.8)
# B. PS 0006 – Sobressalentes (2 sub-itens: 2.1 a 2.2)
# C. PS 0007 – Mapa de Ativos (2 sub-itens: 3.1 a 3.2)
# D. PS 0008 – Disseminação do Conhecimento (3 sub-itens: 4.1 a 4.3)
# E. PS 0009 – Gestão de Infraestrutura (4 sub-itens: 5.1 a 5.4)
# F. PS 0010 – Gestão de Riscos (2 sub-itens: 6.1 a 6.2)
# G. PS 0011 – Interface com a TI (2 sub-itens: 7.1 a 7.2)
# H. PS 0012 – Recursos de Software e Hardware (4 sub-itens: 8.1 a 8.4)
# I. PS 0015 – CyberSegurança (7 sub-itens: 9.1 a 9.7)
# TOTAL: 34 sub-itens

REGRAS_GERAIS = """
REGRAS OFICIAIS DE AVALIAÇÃO (PO.AUT.002 Rev3):

1. PRAZO: Evidências devem ter data < 12 meses da data da auditoria. Após 7 dias da auditoria,
   documentos mais antigos que 12 meses não são válidos para nenhum critério.

2. SAP: Qualquer critério que mencione SAP exige ordem/registro documentado no sistema.
   Print de tela ou relato verbal não substitui ordem SAP formal.

3. HD EXTERNO (sub-item 1.2 Redundância): HD externo é válido para o critério BOM (nota 3).
   A nota EXCELENTE (4) exige servidor com redundância de HD OU ferramenta de versionamento
   centralizada. HD externo sozinho não garante nota 4.

4. KPI ARMP (sub-item 1.8): O KPI deve estar definido no SIG, separado por área e referente
   ao ano atual. KPI de ano anterior ou não separado por área = avaliação prejudicada.

5. ACESSO REMOTO (sub-item 9.2): REGRA HARD — Utilização de ferramentas NÃO HOMOLOGADAS
   (TeamViewer, AnyDesk, etc.) para acesso remoto = NOTA 0 automática (Não tem prática).

6. MANUTENÇÃO PREVENTIVA (sub-item 1.7): Considerar APENAS CLPs neste sub-item.
   Drives, supervisórios e demais ativos NÃO são avaliados neste critério específico.

7. SOBRESSALENTES CRÍTICOS: Foco nos equipamentos classificados como criticidade 1 e A.
   A quantidade deve ser conferida in loco e divergências documentadas com plano de ação no SAP.

8. EVIDÊNCIA FOTOGRÁFICA: Para critérios de inspeção física, foto sem data ou localização
   identificável não é válida como evidência.
"""

# Estrutura: CRITERIOS[(pratica_num, subitem_idx)] = {
#   'pratica': str,
#   'subitem': str,
#   'descricao': str,          # Título da evidência conforme documento
#   'evidencias_exigidas': str, # O que deve ser apresentado como evidência
#   'regras_especiais': str,    # Regras específicas para este sub-item
#   'niveis': {0: str, 1: str, 2: str, 3: str, 4: str}  # Texto LITERAL do documento
# }

CRITERIOS = {

    # =========================================================
    # PRÁTICA 1 — ROTINAS DE TECNOLOGIA DA AUTOMAÇÃO (PS 0005)
    # =========================================================

    (1, 0): {
        'pratica': '1 – ROTINAS DE TA',
        'subitem': '1.1 – Backup periódico e por evento (PLCs, supervisório e drives)',
        'descricao': 'Evidência: Backup periódico e por evento (PLCs, supervisório e drives)',
        'evidencias_exigidas': (
            'Telas do VersionDog/Octoplant mostrando backups periódicos e por evento; '
            'OU estrutura de pastas organizada com datas; '
            'OU ordem de manutenção cíclica no SAP referente ao backup. '
            'Deve cobrir todos os PLCs, supervisórios e drives.'
        ),
        'regras_especiais': (
            'HD externo aceito SOMENTE na ausência do VersionDog/Octoplant — nota máxima = 3 (Bom). '
            'Com VersionDog/Octoplant ativo, o backup automático garante nota 4. '
            'Deve haver ordem de manutenção no SAP descrevendo a rotina.'
        ),
        'niveis': {
            0: 'Não tem prática: Prática não existe.',
            1: 'Iniciando: Backup após grandes alterações dos principais PLCs, supervisórios e drives.',
            2: 'Regular: Backup após quaisquer alterações dos principais PLCs, supervisórios e drives.',
            3: 'Bom: Backup após quaisquer alterações de todos os PLCs, supervisórios e drives.',
            4: (
                'Excelente: Backup de todos os equipamentos e supervisórios de forma periódica e após '
                'quaisquer alterações conforme ordem de manutenção cíclica no SAP ou realização de backup '
                'automático de todos os PLCs, supervisórios e drivers através da ferramenta de versionamento.'
            )
        },
        'armadilhas': (
            'HD externo sem ordem SAP = no máximo nota 3. Backup sem data visível ou sem cobertura de todos os PLCs/supervisórios = nota reduzida. VersionDog/Octoplant instalado mas sem rotina documentada não garante nota 4.'
        )
    },

    (1, 1): {
        'pratica': '1 – ROTINAS DE TA',
        'subitem': '1.2 – Redundância e organização de backups incluindo supervisórios',
        'descricao': 'Evidência: Redundância e organização de backups incluindo supervisórios',
        'evidencias_exigidas': (
            'Estrutura de pastas organizada em dois locais distintos; '
            'OU servidor com redundância de HD; '
            'OU HD externo atualizado mensalmente com plano de manutenção/ordem SAP; '
            'OU ferramenta de versionamento centralizada.'
        ),
        'regras_especiais': (
            'HD externo (atualizado mensalmente conforme ordem de manutenção cíclica no SAP) '
            'atende ao critério BOM (nota 3). '
            'Para nota EXCELENTE (4): servidor com redundância de HD OU ferramenta de versionamento '
            'com armazenamento centralizado e seguro.'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: 'Iniciando: Backups armazenados de forma organizada em um local específico de fácil acesso.',
            2: (
                'Regular: Backups armazenados de forma organizada em dois locais específicos de fácil acesso '
                'ou em um servidor com redundância de HD.'
            ),
            3: (
                'Bom: Backups armazenados de forma organizada em um local específico de fácil acesso e uma '
                'cópia em HD externo ou outra mídia física (atualizado mensalmente com plano de manutenção).'
            ),
            4: (
                'Excelente: Backups armazenados de forma organizada em dois locais específicos de fácil acesso '
                'ou em um servidor com redundância de HD (atualizado mensalmente conforme ordem de manutenção '
                'cíclica no SAP) ou backups armazenados de forma centralizada e segura em um servidor de versionamento.'
            )
        },
        'armadilhas': (
            'Dois locais distintos significa locais FISICAMENTE separados (não duas pastas no mesmo PC). HD externo aceito para nota 3, mas servidor com redundância de HD exigido para nota 4. Pasta sem organização por data ou sem comprovação de periodicidade não pontua.'
        )
    },

    (1, 2): {
        'pratica': '1 – ROTINAS DE TA',
        'subitem': '1.3 – Teste de Backup em PLCs e Supervisórios',
        'descricao': 'Evidência: Teste de Backup em PLCs e Supervisórios',
        'evidencias_exigidas': (
            'Registros de testes de backup nos PLCs e supervisórios críticos (1 e A); '
            'controle registrado em planilha; prints dos backups realizados; '
            'periodicidade trimestral comprovada.'
        ),
        'regras_especiais': (
            'Os testes devem ser sistemáticos e trimestrais para os ativos críticos (1 e A). '
            'Testes pontuais sem registro formal não atingem nota 3 ou superior.'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: 'Iniciando: Testes ocorrem de forma pontual em alguns PLCs ou Aplicativos de Supervisório.',
            2: 'Regular: Testes ocorrem de forma pontual em todos PLCs e Aplicativos de Supervisório.',
            3: (
                'Bom: Testes ocorrem de forma sistematizada trimestralmente em todos PLCs e Aplicativos de '
                'Supervisório Críticos 1 e A. A verificação é feita por meio de controle registrado em uma '
                'planilha e evidenciado por meio de prints dos backups realizados.'
            ),
            4: (
                'Excelente: Testes ocorrem de forma sistematizada trimestral em todos os PLCs e Aplicativos '
                'de Supervisório Críticos 1 e A.'
            )
        },
        'armadilhas': (
            'Teste pontual sem periodicidade sistemática não atinge nota 3. Testes sem registro formal (planilha de controle) são inválidos. Aplicar somente aos ativos críticos 1 e A — não avaliar todos os ativos.'
        )
    },

    (1, 3): {
        'pratica': '1 – ROTINAS DE TA',
        'subitem': '1.4 – Controle de modificações de automação incluindo supervisórios',
        'descricao': 'Evidência: Controle de modificações de automação incluindo supervisórios',
        'evidencias_exigidas': (
            'Registros de todas as alterações com informações visuais (prints, fotos, apresentações, '
            'relatórios, ordens de manutenção); '
            'login pessoal ou controle de versões com reconhecimento automático de alterações; '
            'ordens de manutenção no SAP ou campo de descrição da ferramenta de versionamento.'
        ),
        'regras_especiais': (
            'Para nota 4 (Excelente): deve haver registro via login pessoal OU controle de versões '
            'com reconhecimento automático de alterações e notificação de diferenças entre versão do '
            'dispositivo e versão do servidor de versionamento, com ordens de manutenção associadas.'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: 'Iniciando: Registro é feito em alterações grandes e somente por algumas pessoas.',
            2: 'Regular: Registro de alterações é feito em todas as alterações, porém somente por algumas pessoas.',
            3: (
                'Bom: Registro de alterações é feito em todas as alterações, por todas as pessoas e há '
                'informações visuais (print, fotos, apresentações, relatórios, ordens de manutenção e etc).'
            ),
            4: (
                'Excelente: Registro de alterações é feito em todas as alterações, por todas as pessoas, '
                'há informações visuais (print, fotos, apresentações, relatórios, etc.) e registro de '
                'interferências via login pessoal ou controle de versões com reconhecimento automático de '
                'alterações e notificação de diferenças entre a versão do dispositivo e a versão do servidor '
                'de versionamento. Para ambos os casos deve haver ordens de manutenção, descrita no campo '
                'de descrição da ferramenta de versionamento.'
            )
        },
        'armadilhas': (
            'Registro sem autor identificado (login pessoal) não atinge nota 4. Print sem data ou contexto não vale como evidência de controle. Apenas registrar o que mudou sem mostrar o antes/depois pode ser insuficiente.'
        )
    },

    (1, 4): {
        'pratica': '1 – ROTINAS DE TA',
        'subitem': '1.5 – Verificação de falhas e alarmes em PLCs e Drives',
        'descricao': 'Evidência: Verificação de falhas e alarmes em PLCs e Drives',
        'evidencias_exigidas': (
            'Evidências de rotina de verificação de falhas e alarmes em PLCs e drives; '
            'registros no SAP (rota de inspeção ou ordem de manutenção); '
            'histórico de ocorrências tratadas.'
        ),
        'regras_especiais': (
            'Para nota 4 (Excelente): deve existir rota de inspeção sistematizada no SAP. '
            'Prática esporádica sem registro não atinge nota 3.'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: 'Iniciando: Prática existe de forma esporádica e sem registro formal.',
            2: 'Regular: Prática existe de forma rotineira, porém sem registro formal.',
            3: 'Bom: Prática existe de forma rotineira com registro pontual no sistema de manutenção da fábrica (SAP).',
            4: (
                'Excelente: Prática existe de forma rotineira, acontece de forma sistematizada pelo sistema '
                'de manutenção da fábrica (rota de inspeção no SAP).'
            )
        },
        'armadilhas': (
            'Verificação informal (verbal ou de memória) sem registro no SAP = máximo nota 2. Rota de inspeção exigida no SAP para nota 4. Drives sem registro próprio de falhas podem prejudicar a nota.'
        )
    },

    (1, 5): {
        'pratica': '1 – ROTINAS DE TA',
        'subitem': '1.6 – Verificação de redes de automação',
        'descricao': 'Evidência: Verificação de redes de automação',
        'evidencias_exigidas': (
            'Registros de certificação/verificação das redes de automação; '
            'periodicidade conforme padrão exigido da rede; '
            'documentação e histórico registrados no SAP.'
        ),
        'regras_especiais': (
            'A periodicidade deve ser conforme o padrão exigido de cada tipo de rede. '
            'Para nota 4: documentação e histórico devem estar registrados no SAP.'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: 'Iniciando: Certificação de redes apenas quando elas apresentam problema.',
            2: 'Regular: Rotina de certificação das redes em grandes reparos ou de forma esporádica.',
            3: 'Bom: Rotina de certificação das redes com periodicidade conforme padrão exigido da rede.',
            4: (
                'Excelente: Rotina de certificação das redes com periodicidade conforme padrão exigido '
                'da rede com documentação e histórico registrados no SAP.'
            )
        },
        'armadilhas': (
            'Certificação de rede sem periodicidade ou somente visual não atinge nota 3. Cada tipo de rede tem periodicidade própria — não confundir. Relatório de certificação desatualizado (> 12 meses) não é válido.'
        )
    },

    (1, 6): {
        'pratica': '1 – ROTINAS DE TA',
        'subitem': '1.7 – Manutenção preventiva dos ativos',
        'descricao': 'Evidência: Manutenção preventiva dos ativos',
        'evidencias_exigidas': (
            'Plano de manutenção preventiva no SAP (PDM); '
            'ordens de manutenção executadas; '
            'registros de limpeza e inspeção dos CLPs. '
            'ATENÇÃO: Avaliar APENAS CLPs neste sub-item.'
        ),
        'regras_especiais': (
            '⚠️ REGRA ESPECIAL: Considerar APENAS CLPs neste sub-item. '
            'Drives, supervisórios, IHMs e demais ativos NÃO devem ser avaliados aqui. '
            'Para nota 4: a rotina deve ser demandada pelo plano de manutenção do SAP (PDM/SAP).'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: (
                'Iniciando: Rotina de manutenção preventiva (limpeza, inspeção etc.) acontece após '
                'incidência de problemas nos ativos.'
            ),
            2: (
                'Regular: Rotina de manutenção preventiva (limpeza, inspeção etc.) acontece em grandes '
                'paradas sob demanda da equipe (sem registro no SAP).'
            ),
            3: (
                'Bom: Rotina de manutenção (limpeza, inspeção etc.) acontece em grandes paradas sob '
                'demanda da equipe (registro no SAP).'
            ),
            4: (
                'Excelente: Rotina de manutenção preventiva (limpeza, inspeção etc.) acontece em paradas '
                'sob demanda do plano de manutenção (SAP).'
            )
        },
        'armadilhas': (
            '⚠️ SOMENTE CLPs! Drives, supervisórios e IHMs NÃO entram neste subitem. PDM no SAP sem registros de execução das ordens não comprova a prática. Plano preventivo não vinculado ao SAP (ex.: planilha avulsa) não garante nota 4.'
        )
    },

    (1, 7): {
        'pratica': '1 – ROTINAS DE TA',
        'subitem': '1.8 – Indisponibilidade do Processo Produtivo pela Automação',
        'descricao': 'Evidência: Indisponibilidade do Processo Produtivo pela Automação',
        'evidencias_exigidas': (
            'KPI de indisponibilidade do processo produtivo por falhas de automação; '
            'meta definida no SIG; '
            'KPI separado por área e referente ao ano atual. '
            'Comprovação de desvio em relação à meta.'
        ),
        'regras_especiais': (
            'O KPI deve estar definido no SIG, separado por área e referente ao ano atual. '
            'KPI de ano anterior ou não separado por área = avaliação prejudicada (não atinge nota máxima). '
            'Desvio até 20% da meta = nota 2. Desvio até 10% da meta = nota 3. '
            'Cumprimento de 100% da meta = nota 4.'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: 'Iniciando: Tem controle sobre o KPI e a meta definida no SIG.',
            2: 'Regular: Tem controle sobre o KPI e a meta definida no SIG. Desvio até 20% da meta.',
            3: 'Bom: Tem controle sobre o KPI e a meta definida no SIG. Desvio até 10% da meta.',
            4: 'Excelente: Tem controle sobre o KPI e a meta definida no SIG. Cumprimento de 100% da meta.'
        },
        'armadilhas': (
            'KPI de ano anterior não é válido. KPI não separado por área prejudica a nota. KPI não definido no SIG = não atinge nota 4. Meta sem acompanhamento mensal documentado não atinge nota 3.'
        )
    },

    # =========================================================
    # PRÁTICA 2 — SOBRESSALENTES (PS 0006)
    # =========================================================

    (2, 0): {
        'pratica': '2 – SOBRESSALENTES',
        'subitem': '2.1 – Verificação de sobressalentes de automação',
        'descricao': 'Evidência: Verificação de sobressalentes de automação',
        'evidencias_exigidas': (
            'Listas de sobressalentes com inspeção registrada; '
            'ordens SAP com descrição da conferência in loco; '
            'fotos dos sobressalentes; '
            'evidência de testes a quente dos críticos (1 e A); '
            'avaliação dos níveis de estoque; '
            'ações para corrigir divergências quando identificadas.'
        ),
        'regras_especiais': (
            'Na ordem do SAP deve estar descrito que os itens em estoque são conferidos in loco. '
            'Caso a quantidade seja divergente, isso deverá ser mencionado e evidenciado as ações para corrigir. '
            'Foco nos equipamentos críticos (classificação 1 e A).'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: (
                'Iniciando: Os sobressalentes da área e/ou almoxarifado central são verificados somente '
                'após grandes paradas ou necessidades de ampliações.'
            ),
            2: (
                'Regular: Os sobressalentes da área e/ou almoxarifado central são verificados por alguns '
                'inspetores sem registro no SAP.'
            ),
            3: (
                'Bom: Existe rotina de inspeção dos sobressalentes da área e/ou almoxarifado central, '
                'bem como avaliação dos níveis de estoque, com registro manual no sistema de manutenção (SAP).'
            ),
            4: (
                'Excelente: Existe rotina de inspeção e testes a quente dos sobressalentes da área e/ou '
                'almoxarifado central, dos críticos (1 e A), bem como avaliação dos níveis de estoque, com '
                'solicitações rotineiras no sistema de manutenção (SAP). Na ordem do SAP deve estar descrito '
                'que os itens que estão em estoque são conferidos in loco. Caso a quantidade seja divergente, '
                'isso deverá ser mencionado e evidenciado as ações para corrigir.'
            )
        },
        'armadilhas': (
            'Verificação visual sem registro formal no SAP não é válida. Lista desatualizada ou sem data de última conferência prejudica. Sobressalentes sem identificação de criticidade (1 e A) podem inflar a nota.'
        )
    },

    (2, 1): {
        'pratica': '2 – SOBRESSALENTES',
        'subitem': '2.2 – Equipamentos que possuem sobressalente',
        'descricao': 'Evidência: Equipamentos que possuem sobressalente',
        'evidencias_exigidas': (
            'Lista de equipamentos críticos (1 e A) com indicação de sobressalente disponível; '
            'parametrização no SAP; '
            'quantidades definidas e justificativa dos quesitos avaliados para definição da quantidade ideal; '
            'documento oficial no SIG com a formalização da quantidade ideal.'
        ),
        'regras_especiais': (
            'Para nota 4 (Excelente): deve apresentar quais quesitos foram avaliados para definição '
            'da quantidade ideal de sobressalentes, formalizada em documento oficial no SIG. '
            'Foco nos equipamentos classificados como críticos (1 e A).'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: 'Iniciando: Parte dos equipamentos de automação críticos 1 e A possuem sobressalentes.',
            2: (
                'Regular: Todos os equipamentos de automação críticos 1 e A possuem sobressalentes com '
                'parametrização no SAP.'
            ),
            3: (
                'Bom: Todos os equipamentos de automação críticos 1 e A possuem sobressalentes com '
                'parametrização no SAP e em quantidades suficientes.'
            ),
            4: (
                'Excelente: Todos os equipamentos de automação críticos 1 e A possuem sobressalentes e '
                'em quantidades suficientes. Apresentar quais quesitos foram avaliados para definição da '
                'quantidade ideal de sobressalentes formalizada em documento oficial no SIG.'
            )
        },
        'armadilhas': (
            'Lista de equipamentos sem critério de definição (justificativa do por quê tem/não tem sobressalente) não atinge nota 4. Equipamentos críticos 1 e A sem sobressalente identificado = pontuação zero neste item. Conferência não feita in loco = não válida.'
        )
    },

    # =========================================================
    # PRÁTICA 3 — MAPA DE ATIVOS (PS 0007)
    # =========================================================

    (3, 0): {
        'pratica': '3 – MAPA DE ATIVOS',
        'subitem': '3.1 – Mapa dos ativos de automação para Power BI — Planilha de Hardware',
        'descricao': 'Evidência: Mapa dos ativos de automação para Power BI — Planilha de Hardware',
        'evidencias_exigidas': (
            'Planilha de hardware com todos os equipamentos listados e informações completas; '
            'lista técnica no SAP; '
            'ordem cíclica no SAP para atualização anual; '
            'evidência de atualização sistemática conforme entrada de novos equipamentos ou substituição.'
        ),
        'regras_especiais': (
            'Para nota 4 (Excelente): deve ter lista técnica no SAP e ordem cíclica no SAP para '
            'atualizar a planilha anualmente.'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: (
                'Iniciando: Listados os principais equipamentos de automação. '
                'Lista não é atualizada ou não preenchida corretamente.'
            ),
            2: (
                'Regular: Listados os principais equipamentos de automação com todas as informações '
                'preenchidas. Lista não é atualizada.'
            ),
            3: (
                'Bom: Listados todos os equipamentos de automação com todas as informações preenchidas. '
                'Atualização sistemática da lista conforme entrada de novos equipamentos ou substituição do existente.'
            ),
            4: (
                'Excelente: Listados todos os equipamentos de automação com todas as informações preenchidas. '
                'Atualização sistemática da lista conforme entrada de novos equipamentos ou substituição do '
                'existente. Ter lista técnica no SAP. Atualização sistemática da lista conforme entrada de novos '
                'equipamentos ou substituição do existente. Ter ordem cíclica no SAP para atualizar a planilha anualmente.'
            )
        },
        'armadilhas': (
            'Planilha desatualizada (> 12 meses) não é válida. Lista técnica no SAP exigida para nota 4. Campos obrigatórios em branco (IP, versão de firmware, etc.) reduzem a nota.'
        )
    },

    (3, 1): {
        'pratica': '3 – MAPA DE ATIVOS',
        'subitem': '3.2 – Mapa de softwares de automação para Power BI',
        'descricao': 'Evidência: Mapa de softwares de automação para Power BI',
        'evidencias_exigidas': (
            'Planilha de softwares com todos os itens listados e informações completas; '
            'ordem cíclica no SAP para atualização anual; '
            'atualização via árvore de projeto da ferramenta de versionamento.'
        ),
        'regras_especiais': (
            'Para nota 4 (Excelente): deve ter ordem cíclica no SAP para atualizar a planilha anualmente '
            'e atualização sistemática via árvore de projeto da ferramenta de versionamento.'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: (
                'Iniciando: Listados os principais softwares de automação. '
                'Lista não é atualizada ou não preenchida corretamente.'
            ),
            2: (
                'Regular: Listados os principais softwares de automação com todas as informações preenchidas. '
                'Lista não é atualizada.'
            ),
            3: (
                'Bom: Listados todos os softwares de automação com todas as informações preenchidas. '
                'Lista não é atualizada.'
            ),
            4: (
                'Excelente: Listados todos os softwares de automação com todas as informações preenchidas. '
                'Atualização sistemática da lista conforme instalação de novos softwares ou atualização do existente. '
                'Atualização sistemática da lista através da árvore de projeto da ferramenta de versionamento. '
                'Ter ordem cíclica no SAP para atualizar a planilha anualmente.'
            )
        },
        'armadilhas': (
            'Planilha de softwares sem versão, licença ou localização = nota reduzida. Ordem cíclica no SAP para atualização exigida para nota 4. Softwares de terceiros não mapeados são uma falha comum.'
        )
    },

    # =========================================================
    # PRÁTICA 4 — DISSEMINAÇÃO DO CONHECIMENTO (PS 0008)
    # =========================================================

    (4, 0): {
        'pratica': '4 – DISSEMINAÇÃO DO CONHECIMENTO',
        'subitem': '4.1 – Treinamentos de automação para a equipe de manutenção',
        'descricao': 'Evidência: Treinamentos de automação para a equipe de manutenção',
        'evidencias_exigidas': (
            'Mapa dos treinamentos necessários por cargo; '
            'cronograma de treinamentos; '
            'registros de treinamentos realizados; '
            'rotina de atualização definida.'
        ),
        'regras_especiais': (
            'Para nota 3 (Bom): cronograma definido porém em atraso. '
            'Para nota 4 (Excelente): cronograma definido e em dia, com rotina de atualização definida.'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: 'Iniciando: Mapa dos treinamentos necessários por cargo.',
            2: (
                'Regular: Mapa dos treinamentos necessários por cargo. '
                'Algumas pessoas da equipe treinadas de acordo com o mapeamento sem cronograma definido de atualização.'
            ),
            3: (
                'Bom: Mapa dos treinamentos necessários por cargo. '
                'Cronograma de treinamentos definidos porém em Atraso.'
            ),
            4: (
                'Excelente: Mapa dos treinamentos necessários por cargo. '
                'Cronograma de treinamentos definidos e em dia. Rotina de atualização definida.'
            )
        },
        'armadilhas': (
            'Cronograma definido mas em atraso = no máximo nota 3. Treinamentos sem comprovação de realização (certificados, listas de presença) não valem. Mapa de treinamentos sem vinculação por cargo não atinge nota 4.'
        )
    },

    (4, 1): {
        'pratica': '4 – DISSEMINAÇÃO DO CONHECIMENTO',
        'subitem': '4.2 – Levantamento de treinamentos necessários (responsável(is) de automação)',
        'descricao': 'Evidência: Levantamento de treinamentos necessários (responsável(is) de automação)',
        'evidencias_exigidas': (
            'Mapeamento de todos os treinamentos necessários para o(s) responsável(is) de automação; '
            'cronograma de treinamentos; '
            'rotina de atualização definida.'
        ),
        'regras_especiais': (
            'Este sub-item é específico para os responsáveis de automação (não toda a equipe). '
            'Para nota 4: cronograma em dia com rotina de atualização definida.'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: (
                'Iniciando: Mapeamento dos principais treinamentos necessários para o responsável(is) '
                'de automação.'
            ),
            2: (
                'Regular: Mapeamento de todos os treinamentos necessários para o responsável(is) '
                'de automação.'
            ),
            3: (
                'Bom: Mapeamento de todos os treinamentos necessários para o responsável(is) de automação. '
                'Cronograma de treinamentos definidos porém em Atraso.'
            ),
            4: (
                'Excelente: Mapeamento de todos os treinamentos necessários para o responsável(is) de '
                'automação. Cronograma de treinamentos definidos e em dia. Rotina de atualização definida.'
            )
        },
        'armadilhas': (
            'Sub-item específico para o(s) responsável(is) de automação — não considerar equipe toda. Treinamento planejado mas não realizado = nota 2 no máximo. Certificado de treinamento vencido (> 12 meses para renováveis) não é válido.'
        )
    },

    (4, 2): {
        'pratica': '4 – DISSEMINAÇÃO DO CONHECIMENTO',
        'subitem': '4.3 – Apresentação de boas práticas',
        'descricao': 'Evidência: Apresentação de boas práticas',
        'evidencias_exigidas': (
            'Registros de apresentações de projetos e melhorias realizadas; '
            'comprovação de participação nas reuniões de disseminação; '
            'evidência de apresentação para outras áreas da unidade.'
        ),
        'regras_especiais': (
            'Para nota 3 (Bom): participação em mais de 50% das reuniões. '
            'Para nota 4 (Excelente): participação em mais de 80% das reuniões.'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: 'Iniciando: Apresentação de projetos e melhorias realizadas para demais colaboradores da área.',
            2: (
                'Regular: Apresentação de projetos e melhorias realizadas para todas as áreas da unidade '
                'de forma sistematizada.'
            ),
            3: (
                'Bom: Apresentação de projetos e melhorias realizadas para todas as áreas da unidade de '
                'forma sistematizada. (Participação da área em mais que 50% das Reuniões)'
            ),
            4: (
                'Excelente: Apresentação de projetos e melhorias realizadas para todas as áreas da unidade '
                'de forma sistematizada. (Participação da área em mais que 80% das Reuniões)'
            )
        },
        'armadilhas': (
            'Participação abaixo de 50% das reuniões = não atinge nota 3. Apresentação sem registro (ata, print, arquivo) não é válida. Boas práticas sem compartilhamento formal com outras unidades não atingem nota 4.'
        )
    },

    # =========================================================
    # PRÁTICA 5 — GESTÃO DE INFRAESTRUTURA (PS 0009)
    # =========================================================

    (5, 0): {
        'pratica': '5 – GESTÃO DE INFRAESTRUTURA',
        'subitem': '5.1 – Alimentação redundante (Nobreak)',
        'descricao': 'Evidência: Alimentação redundante (Nobreak)',
        'evidencias_exigidas': (
            'Comprovação de alimentação via nobreak para equipamentos críticos (1 e A); '
            'registros de testes de nobreak no SAP (PDM cíclico); '
            'manutenção preventiva registrada no SAP.'
        ),
        'regras_especiais': (
            'Para nota 4 (Excelente): deve haver rotina formal de testes e manutenção preventiva '
            'registradas no SAP (PDM cíclico). O nobreak deve estar em funcionamento comprovado.'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: (
                'Iniciando: Alimentação de alguns equipamentos críticos (1 e A) de automação é realizada '
                'por nobreak, porém não há rotina de testes.'
            ),
            2: (
                'Regular: Alimentação de alguns equipamentos críticos (1 e A) de automação é realizada '
                'por nobreak e há rotina de testes.'
            ),
            3: (
                'Bom: Alimentação de todos os equipamentos críticos (1 e A) de automação é realizada '
                'por nobreak, há uma rotina informal de testes.'
            ),
            4: (
                'Excelente: Alimentação de todos os equipamentos críticos (1 e A) de automação é realizada '
                'por nobreak, está em funcionamento, há uma rotina formal de testes e manutenção preventiva '
                'registradas no SAP (PDM cíclico).'
            )
        },
        'armadilhas': (
            'Nobreak sem laudo de manutenção preventiva = no máximo nota 3. Cobertura parcial dos equipamentos críticos (1 e A) reduz a nota. Nobreak instalado mas sem teste documentado não garante nota 4.'
        )
    },

    (5, 1): {
        'pratica': '5 – GESTÃO DE INFRAESTRUTURA',
        'subitem': '5.2 – Lista de IPs e IO',
        'descricao': 'Evidência: Lista de IPs e IO',
        'evidencias_exigidas': (
            'Lista de IPs atualizada de todos os PLCs; '
            'lista de IO (entradas/saídas) atualizada de todos os PLCs; '
            'sistemática de verificação via SAP ou ferramenta de versionamento.'
        ),
        'regras_especiais': (
            'Para nota 4 (Excelente): deve existir sistemática de verificação via SAP ou '
            'ferramenta de Versionamento que garanta a atualização das listas.'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: (
                "Iniciando: Lista de IP's ou Lista de IO de alguns PLCs existentes, porém desatualizada."
            ),
            2: (
                "Regular: Lista de IP's e Lista de IO de todos os PLCs existentes, porém desatualizada."
            ),
            3: (
                "Bom: Lista de IP's e Lista de IO de todos os PLCs existentes e atualizadas."
            ),
            4: (
                "Excelente: Lista de IP's e Lista de IO de todos os PLCs existentes e atualizadas, com "
                'sistemática de verificação via SAP ou ferramenta de Versionamento.'
            )
        },
        'armadilhas': (
            'Lista de IPs desatualizada ou sem data = nota reduzida. Lista de IO sem vinculação com os equipamentos físicos = insuficiente. Sistemática de verificação via SAP exigida para nota 4.'
        )
    },

    (5, 2): {
        'pratica': '5 – GESTÃO DE INFRAESTRUTURA',
        'subitem': '5.3 – Diagrama de rede e Desenhos Elétricos',
        'descricao': 'Evidência: Diagrama de rede e Desenhos Elétricos',
        'evidencias_exigidas': (
            'Diagrama de rede de automação; '
            'desenhos elétricos dos sistemas de automação; '
            'versão em papel e/ou digital atualizada; '
            'para nota 4: documentos no Meridian.'
        ),
        'regras_especiais': (
            'Para nota 4 (Excelente): desenhos e diagramas em papel e documento digital atualizados '
            'devem estar no Meridian (sistema de gestão de documentos técnicos).'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: (
                'Iniciando: Desenhos e diagramas de automação existentes em papel, '
                'centralizados nas salas elétricas.'
            ),
            2: (
                'Regular: Desenhos e diagramas de automação existentes em papel e documento digital '
                '(qualquer um dos dois desatualizados) centralizados sob gestão interna da área.'
            ),
            3: (
                'Bom: Desenhos e diagramas de automação existentes em papel e documento digital '
                '(atualizados) centralizados sob gestão interna da área.'
            ),
            4: (
                'Excelente: Desenhos e diagramas de automação existentes em papel e documento digital '
                '(atualizados) no Meridian.'
            )
        },
        'armadilhas': (
            'Diagrama de rede sem data de atualização ou desatualizado = nota reduzida. Desenhos elétricos em papel sem versão digital não atingem nota 4. Diagrama que não reflete a topologia real é considerado inválido.'
        )
    },

    (5, 3): {
        'pratica': '5 – GESTÃO DE INFRAESTRUTURA',
        'subitem': '5.4 – Gestão do ciclo de vida de ativos',
        'descricao': 'Evidência: Gestão do ciclo de vida de ativos',
        'evidencias_exigidas': (
            'Lista de ativos com data de fim de ciclo de vida conhecida; '
            'cadastro na matriz de risco da unidade; '
            'estratégia de troca definida com data.'
        ),
        'regras_especiais': (
            'Para nota 4 (Excelente): todos os ativos devem ter data de fim de ciclo de vida conhecida, '
            'cadastrada na matriz de risco com data e estratégia de troca definidas.'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: 'Iniciando: Fim do ciclo de vida dos principais ativos (criticidade A) conhecidos.',
            2: (
                'Regular: Fim do ciclo de vida dos principais ativos (criticidade A) conhecidos e '
                'cadastrados na matriz de risco da unidade.'
            ),
            3: (
                'Bom: Fim do ciclo de vida de todos os ativos conhecidos e cadastrados na matriz de '
                'risco da unidade.'
            ),
            4: (
                'Excelente: Fim do ciclo de vida de todos os ativos conhecidos e cadastrados na matriz '
                'de risco da unidade (com data e estratégia de troca).'
            )
        },
        'armadilhas': (
            'Ativos sem data de fim de ciclo de vida = não atinge nota 3. Matriz de risco sem os ativos críticos de automação cadastrados = insuficiente. Plano de ação sem data e responsável = não aceito para nota 4.'
        )
    },

    # =========================================================
    # PRÁTICA 6 — GESTÃO DE RISCOS (PS 0010)
    # =========================================================

    (6, 0): {
        'pratica': '6 – GESTÃO DE RISCOS',
        'subitem': '6.1 – Identificação dos riscos',
        'descricao': 'Evidência: Identificação dos riscos',
        'evidencias_exigidas': (
            'Mapeamento de riscos dos equipamentos de automação; '
            'inclusão na matriz de gestão de risco da área; '
            'atualização sistemática semestral via SAP.'
        ),
        'regras_especiais': (
            'Para nota 3 (Bom): riscos de todos os equipamentos mapeados com atualização por eventos '
            'e inclusão na matriz de gestão de risco. '
            'Para nota 4 (Excelente): atualização sistemática semestral via SAP.'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: 'Iniciando: Mapeamento de riscos dos principais equipamentos.',
            2: 'Regular: Mapeamento de riscos de todos os equipamentos.',
            3: (
                'Bom: Mapeamento de riscos de todos os equipamentos, atualização por eventos e inclusão '
                'desses riscos na matriz de gestão de risco da área.'
            ),
            4: (
                'Excelente: Mapeamento de riscos de todos os equipamentos, atualização sistemática '
                'semestral via SAP.'
            )
        },
        'armadilhas': (
            'Mapeamento parcial (somente equipamentos principais) = no máximo nota 2. Riscos não incluídos na matriz de gestão da unidade = nota reduzida. Atualização anual exigida — risco mapeado há mais de 12 meses = nota 3 no máximo.'
        )
    },

    (6, 1): {
        'pratica': '6 – GESTÃO DE RISCOS',
        'subitem': '6.2 – Planos de contingência',
        'descricao': 'Evidência: Planos de contingência',
        'evidencias_exigidas': (
            'Planos de contingência para todos os riscos levantados; '
            'telefones de contato; '
            'tempo de impacto no processo definido; '
            'atualização sistemática semestral via SAP e/ou anual via vencimento no SIG.'
        ),
        'regras_especiais': (
            'Para nota 4 (Excelente): planos devem incluir telefones de contato, tempo de impacto no '
            'processo, com atualização sistemática semestral via SAP e/ou anual via vencimento no SIG.'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: 'Iniciando: Planos de contingência para os principais riscos levantados.',
            2: 'Regular: Planos de contingência para todos os riscos levantados.',
            3: (
                'Bom: Planos de contingência para todos os riscos levantados, atualização por eventos.'
            ),
            4: (
                'Excelente: Planos de contingência para todos os riscos levantados, incluindo telefones '
                'de contato, tempo de impacto no processo, com atualização sistemática semestral via SAP '
                'e/ou anual via vencimento no SIG.'
            )
        },
        'armadilhas': (
            'Plano de contingência sem telefones de contato e tempo de impacto = no máximo nota 3. Contingência não testada = não atinge nota 4. Plano que não cobre todos os riscos levantados no 6.1 = insuficiente.'
        )
    },

    # =========================================================
    # PRÁTICA 7 — INTERFACE COM A TI (PS 0011)
    # =========================================================

    (7, 0): {
        'pratica': '7 – INTERFACE COM A TI',
        'subitem': '7.1 – Fronteiras de responsabilidades',
        'descricao': 'Evidência: Fronteiras de responsabilidades',
        'evidencias_exigidas': (
            'Documento formal definindo fronteiras de responsabilidade entre TA e TI; '
            'lista de equipamentos de informática com fronteira definida; '
            'evidência de atualização por eventos.'
        ),
        'regras_especiais': (
            'Para nota 4 (Excelente): fronteiras de responsabilidade devem estar definidas '
            'FORMALMENTE (documento oficial), não apenas de forma informal.'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: (
                'Iniciando: Os principais equipamentos de informática com fronteira definida informalmente.'
            ),
            2: (
                'Regular: Os principais equipamentos de informática com fronteira definida informalmente '
                'e atualização por eventos.'
            ),
            3: (
                'Bom: Todos os equipamentos de informática com fronteira definida informalmente e '
                'atualização por eventos.'
            ),
            4: (
                'Excelente: Todos os equipamentos de informática com fronteira definida formalmente e '
                'atualização por eventos.'
            )
        },
        'armadilhas': (
            'Documento informal ou apenas verbal = não atinge nota 3. Fronteiras não definidas formalmente no SIG ou sistema equivalente = não atinge nota 4. Lista de demandas sem histórico de atendimento documentado prejudica a nota.'
        )
    },

    (7, 1): {
        'pratica': '7 – INTERFACE COM A TI',
        'subitem': '7.2 – Projetos integrados (PIMS, MES e VersionDog)',
        'descricao': 'Evidência: Projetos integrados (PIMS, MES e VersionDog)',
        'evidencias_exigidas': (
            'Comprovação de treinamento formal dos responsáveis de automação nos softwares integrados; '
            'conhecimento para análise de logs de falhas de comunicação TA/TI; '
            'documentação dos projetos integrados disponível no SAP ou SIG.'
        ),
        'regras_especiais': (
            'Para nota 4 (Excelente): toda a documentação dos projetos integrados deve estar disponível '
            'no SAP ou SIG (não apenas localmente). '
            'Treinamento deve ser formal (não informal).'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: (
                'Iniciando: Responsável(is) de automação das áreas com treinamento informal na '
                'utilização dos principais softwares.'
            ),
            2: (
                'Regular: Responsável(is) de automação das áreas com treinamento formal na utilização '
                'dos principais softwares.'
            ),
            3: (
                'Bom: Responsável(is) de automação das áreas com treinamento formal na utilização dos '
                'principais softwares, conhecimento para análise dos logs de falhas de comunicação entre '
                'as interfaces TA/TI, com documentação parcial dos projetos integrados disponíveis localmente.'
            ),
            4: (
                'Excelente: Responsável(is) de automação das áreas com treinamento formal na utilização '
                'de todos os softwares, conhecimento para análise dos logs de falhas de comunicação entre '
                'as interfaces TA/TI, com toda a documentação dos projetos integrados disponíveis no SAP ou SIG.'
            )
        },
        'armadilhas': (
            'Treinamento sem comprovação (certificado, lista de presença) = não válido. Documentação do projeto fora do sistema (ex.: somente e-mail) = não atinge nota 4. Integração parcial (somente um dos sistemas) = nota reduzida.'
        )
    },

    # =========================================================
    # PRÁTICA 8 — RECURSOS DE SOFTWARE E HARDWARE (PS 0012)
    # =========================================================

    (8, 0): {
        'pratica': '8 – RECURSOS DE SOFTWARE E HARDWARE',
        'subitem': '8.1 – Computadores de engenharia, clientes e IHM',
        'descricao': 'Evidência: Computadores de engenharia, clientes e IHM',
        'evidencias_exigidas': (
            'Inventário de computadores de supervisório e engenharia; '
            'comprovação de não obsolescência; '
            'evidência de rotina de troca periódica ou hot-standby. '
            'Mínimo: 2 computadores para cada aplicativo de supervisório e '
            '2 computadores com softwares de engenharia.'
        ),
        'regras_especiais': (
            'Número adequado mínimo: 2 computadores para cada aplicativo de supervisório e '
            '2 computadores com os softwares de engenharia. '
            'Para nota 4: computadores não obsoletos com rotina de troca periódica OU '
            'computadores reserva em regime hot-standby.'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: (
                'Iniciando: Existência de computadores utilizados para estações de supervisórios e '
                'engenharia em número adequado (mínimo de 2 computadores para cada aplicativo de '
                'supervisório e mínimo de 2 computadores com os softwares de engenharia).'
            ),
            2: (
                'Regular: Existência de computadores utilizados para estações de supervisórios e '
                'engenharia em número adequado. Principais computadores utilizados para fins de '
                'automação não obsoletos.'
            ),
            3: (
                'Bom: Existência de computadores utilizados para estações de supervisórios e engenharia '
                'em número adequado. Todos os computadores utilizados para fins de automação não obsoletos.'
            ),
            4: (
                'Excelente: Existência de computadores utilizados para estações de supervisórios e '
                'engenharia em número adequado. Todos os computadores utilizados para fins de automação '
                'não obsoletos. Rotina de troca periódica de computadores ou computadores reservas em '
                'regime hot-standby.'
            )
        },
        'armadilhas': (
            'Computadores obsoletos (SO fora de suporte) = nota reduzida automaticamente. Menos de 2 computadores por aplicativo de supervisório = não atinge nota 3. Inventário sem data de atualização ou desatualizado = insuficiente.'
        )
    },

    (8, 1): {
        'pratica': '8 – RECURSOS DE SOFTWARE E HARDWARE',
        'subitem': '8.2 – Computadores Stand Alone e/ou Servidores',
        'descricao': 'Evidência: Computadores Stand Alone e/ou Servidores',
        'evidencias_exigidas': (
            'Comprovação de redundância de HD nos servidores; '
            'redundância de fonte de alimentação; '
            'servidor de backup em local diferente do servidor principal; '
            'comprovação de não obsolescência (peças de reposição de fácil aquisição).'
        ),
        'regras_especiais': (
            'Para nota 4 (Excelente): servidor de backup deve estar armazenado em local diferente '
            'do servidor principal. Servidores não obsoletos com peças de reposição de fácil aquisição.'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: 'Iniciando: Servidor de dados com redundância de HD.',
            2: 'Regular: Servidor de dados com redundância de HD e fonte de alimentação.',
            3: (
                'Bom: Servidor de dados com redundância de HD e fonte de alimentação. '
                'Servidor não obsoleto (peças de reposição de fácil aquisição).'
            ),
            4: (
                'Excelente: Servidor de dados com redundância. Servidor de backup armazenado em local '
                'diferente do servidor principal. Servidores não obsoletos (peças de reposição de fácil aquisição).'
            )
        },
        'armadilhas': (
            'Servidor sem redundância de HD = não atinge nota 4. Servidor de backup no mesmo rack/sala = não atinge nota 4. Fonte redundante ausente nos equipamentos críticos = nota reduzida.'
        )
    },

    (8, 2): {
        'pratica': '8 – RECURSOS DE SOFTWARE E HARDWARE',
        'subitem': '8.3 – Teste de Redundância',
        'descricao': 'Evidência: Teste de Redundância',
        'evidencias_exigidas': (
            'Registros de testes de redundância entre servidor principal e redundante; '
            'procedimento formalizado e documentado; '
            'verificação da transferência entre servidores; '
            'OU comprovação de arquitetura standalone (não se aplica).'
        ),
        'regras_especiais': (
            'Em caso de arquitetura Standalone onde não se aplica teste de redundância, '
            'isso deve ser comprovado — neste caso a nota Excelente (4) é aplicável. '
            'Para nota 4: testes periódicos com simulação de falhas controladas e verificação completa.'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: (
                'Iniciando: Os testes são realizados de forma esporádica, sem periodicidade definida, '
                'sem procedimento formal ou com documentação mínima e inconsistente.'
            ),
            2: (
                'Regular: Testes de redundância são realizados com alguma regularidade, mas a periodicidade '
                'pode ser irregular ou não totalmente aderente a um padrão.'
            ),
            3: (
                'Bom: Testes de redundância são realizados periodicamente conforme um procedimento '
                'formalizado e documentado. A transferência entre servidor principal e redundante é '
                'verificada de forma consistente.'
            ),
            4: (
                'Excelente: O teste de redundância é realizado de forma periódica, abrangente e otimizada. '
                'Procedimentos formalizados, atualizados e simulação de falhas controladas com verificação '
                'completa. (Ou arquitetura Standalone onde não se aplica).'
            )
        },
        'armadilhas': (
            'Arquitetura Standalone sem justificativa formal = não aceito. Teste de redundância sem procedimento e registro = não atinge nota 3. Teste realizado uma única vez sem periodicidade = no máximo nota 2.'
        )
    },

    (8, 3): {
        'pratica': '8 – RECURSOS DE SOFTWARE E HARDWARE',
        'subitem': '8.4 – Softwares e IHM',
        'descricao': 'Evidência: Softwares e IHM',
        'evidencias_exigidas': (
            'Inventário de softwares necessários para todos os equipamentos de automação; '
            'comprovação de sistema operacional atualizado em todos os computadores de automação.'
        ),
        'regras_especiais': (
            'Para nota 3 (Bom): principais computadores com sistema operacional atualizado. '
            'Para nota 4 (Excelente): TODOS os computadores com sistema operacional atualizado.'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: (
                'Iniciando: Todos os softwares necessários para configuração e programação dos '
                'principais equipamentos de automação.'
            ),
            2: (
                'Regular: Todos os softwares necessários para configuração e programação de todos '
                'os equipamentos de automação.'
            ),
            3: (
                'Bom: Todos os softwares necessários para configuração e programação de todos os '
                'equipamentos de automação. Os principais computadores com sistema operacional atualizado.'
            ),
            4: (
                'Excelente: Todos os softwares necessários para configuração e programação de todos '
                'os equipamentos de automação. Todos os computadores com sistema operacional atualizado.'
            )
        },
        'armadilhas': (
            'Software sem licença válida = nota 0 automática (risco jurídico). Sistema operacional fora de suporte nos computadores principais = não atinge nota 4. IHM sem software de configuração disponível = reduz a nota.'
        )
    },

    # =========================================================
    # PRÁTICA 9 — CYBERSEGURANÇA (PS 0015)
    # =========================================================

    (9, 0): {
        'pratica': '9 – CYBERSEGURANÇA',
        'subitem': '9.1 – Treinamento de Cybersecurity',
        'descricao': 'Evidência: Treinamento de Cybersecurity',
        'evidencias_exigidas': (
            'Registros de treinamento de cybersecurity do ano atual para a equipe; '
            'comprovação de treinamento do ano anterior (para nota 4). '
            'Mínimo 50% da equipe com treinamento do ano anterior para nota Excelente.'
        ),
        'regras_especiais': (
            'Treinamento deve ser do ano atual. '
            'Para nota 4 (Excelente): treinamento do ano atual completo E '
            'treinamento do ano anterior incompleto para no mínimo 50% da equipe.'
        ),
        'niveis': {
            0: 'Não tem prática: A prática não existe.',
            1: (
                'Iniciando: Treinamento do ano atual incompleto para algumas pessoas da equipe (>50%).'
            ),
            2: (
                'Regular: Treinamento do ano atual incompleto para todas as pessoas da equipe OU '
                'Treinamento do ano atual completo para algumas pessoas da equipe (>50%).'
            ),
            3: 'Bom: Treinamento do ano atual completo para toda a equipe.',
            4: (
                'Excelente: Treinamento do ano atual completo e Treinamento do ano anterior incompleto '
                'para no mínimo 50% da equipe.'
            )
        },
        'armadilhas': (
            'Treinamento de ano anterior não é válido para nota 4. Participação parcial da equipe sem justificativa = nota reduzida. Treinamento sem registro (certificado/lista de presença) = não aceito.'
        )
    },

    (9, 1): {
        'pratica': '9 – CYBERSEGURANÇA',
        'subitem': '9.2 – Acesso remoto',
        'descricao': 'Evidência: Acesso remoto',
        'evidencias_exigidas': (
            'Comprovação de uso EXCLUSIVO de ferramentas homologadas para acesso remoto; '
            'autenticação de dois fatores habilitada; '
            'controle e registro de acessos; '
            'uso de rede corporativa com firewall; '
            'OU logs comprovando ausência de acesso remoto.'
        ),
        'regras_especiais': (
            '⚠️ REGRA HARD: Utilização de ferramentas NÃO HOMOLOGADAS (TeamViewer, AnyDesk, etc.) '
            'para acesso remoto = NOTA 0 automática (Não tem prática). '
            'Para nota 4 (Excelente): uso de rede corporativa com firewall OU '
            'comprovação com extração de logs de ausência de utilização.'
        ),
        'niveis': {
            0: (
                'Não tem prática: Utilização de ferramentas não homologadas para acesso remoto.'
            ),
            1: 'Iniciando: Acesso remoto com autenticação, controle e registro de acessos.',
            2: (
                'Regular: Acesso remoto com autenticação de dois fatores, controle e registro de acessos.'
            ),
            3: (
                'Bom: Acesso remoto com autenticação de dois fatores, controle e registro de acessos, '
                'utilização de rede com firewall.'
            ),
            4: (
                'Excelente: Acesso remoto com autenticação de dois fatores, controle e registro de acessos, '
                'utilização de rede corporativa com firewall. Ou em caso de não utilização, comprovar com '
                'extração de logs.'
            )
        },
        'armadilhas': (
            '⚠️ REGRA HARD: TeamViewer, AnyDesk ou qualquer ferramenta não homologada = NOTA 0 automática. Acesso sem autenticação de dois fatores = não atinge nota 4. Auditoria de sessões ausente = não atinge nota 3.'
        )
    },

    (9, 2): {
        'pratica': '9 – CYBERSEGURANÇA',
        'subitem': '9.3 – Procedimento de backup e recuperação',
        'descricao': 'Evidência: Procedimento de backup e recuperação',
        'evidencias_exigidas': (
            'Procedimento documentado de backup com período de retenção, teste e rastreamento; '
            'lista de sistemas críticos identificados; '
            'comprovação de cópias testadas regularmente.'
        ),
        'regras_especiais': (
            'Para nota 3 (Bom): sistemas críticos devem estar devidamente listados. '
            'Para nota 4 (Excelente): cópias testadas regularmente com procedimento claro.'
        ),
        'niveis': {
            0: 'Não tem prática: Não existe um procedimento de backup definido.',
            1: (
                'Iniciando: Existe o procedimento de backup, mas não está definido um procedimento '
                'de retenção e rastreamento das cópias.'
            ),
            2: (
                'Regular: Existe o procedimento de backup contendo o período de retenção, teste e '
                'rastreamento. Sistemas críticos não estão identificados.'
            ),
            3: (
                'Bom: Existe o procedimento de backup contendo o período de retenção, teste e '
                'rastreamento. Sistemas críticos estão devidamente listados.'
            ),
            4: (
                'Excelente: Procedimento claro com período de retenção, teste e rastreamento. '
                'Sistemas críticos identificados e cópias testadas regularmente.'
            )
        },
        'armadilhas': (
            'Procedimento existente mas sem teste de restauração = não atinge nota 4. Período de retenção não definido = nota reduzida. Backup sem rastreamento de alterações não atinge nota 3.'
        )
    },

    (9, 3): {
        'pratica': '9 – CYBERSEGURANÇA',
        'subitem': '9.4 – Procedimento de resposta a incidentes',
        'descricao': 'Evidência: Procedimento de resposta a incidentes',
        'evidencias_exigidas': (
            'Procedimento documentado para resposta a incidentes de segurança; '
            'matriz RACI definida; '
            'evidência de envolvimento do time de TI da localidade.'
        ),
        'regras_especiais': (
            'Para nota 3 (Bom): procedimento deve conter matriz RACI definida. '
            'Para nota 4 (Excelente): procedimento com RACI e time de TI da localidade acionado.'
        ),
        'niveis': {
            0: 'Não tem prática: Não existem procedimentos.',
            1: (
                'Iniciando: Não existem procedimentos definidos. '
                'Membros acionam o Supervisor em caso de ocorrências.'
            ),
            2: (
                'Regular: Existe um procedimento mínimo a ser seguido apenas em casos de emergência.'
            ),
            3: (
                'Bom: O procedimento para casos de incidentes existe e contém a matriz RACI definida.'
            ),
            4: (
                'Excelente: O procedimento existe, tem matriz RACI definida e o time de TI da '
                'localidade será acionado.'
            )
        },
        'armadilhas': (
            'Procedimento sem matriz RACI = não atinge nota 3. RACI definida mas sem treinamento comprovado dos envolvidos = não atinge nota 4. Incidente sem registro pós-ocorrência = reduz a nota.'
        )
    },

    (9, 4): {
        'pratica': '9 – CYBERSEGURANÇA',
        'subitem': '9.5 – Cultura de atualização',
        'descricao': 'Evidência: Cultura de atualização',
        'evidencias_exigidas': (
            'Procedimento de atualização alinhado com política de estação segura; '
            'envolvimento da TI no processo; '
            'conformidade com último patch de segurança; '
            'atualização de antivírus comprovada.'
        ),
        'regras_especiais': (
            'Para nota 4 (Excelente): estação segura implantada conforme política com apoio da TI, '
            'conformidade com último patch E atualização de antivírus. '
            'Procedimento mínimo sem envolvimento da TI não atinge nota 3.'
        ),
        'niveis': {
            0: 'Não tem prática: Não existem procedimentos.',
            1: (
                'Iniciando: Procedimento mínimo sem envolvimento da TI, '
                'baseado na instalação dos antivírus.'
            ),
            2: (
                'Regular: Procedimento utilizado para qualquer estação/servidor com necessidade '
                'do envolvimento da TI.'
            ),
            3: (
                'Bom: Procedimento alinhado com a política de estação segura e envolve a TI. '
                'Conformidade com o último patch de segurança.'
            ),
            4: (
                'Excelente: Estação segura implantada conforme política com apoio da TI. '
                'Conformidade com último patch e atualização de antivírus.'
            )
        },
        'armadilhas': (
            'Atualizações sem envolvimento da TI (estação segura) = não atinge nota 4. Procedimento existente mas não seguido (evidência de desatualização) = nota reduzida. Atualização realizada sem teste prévio em ambiente seguro = risco e pode reduzir nota.'
        )
    },

    (9, 5): {
        'pratica': '9 – CYBERSEGURANÇA',
        'subitem': '9.6 – Gestão de Acesso físico e lógico',
        'descricao': 'Evidência: Gestão de Acesso físico e lógico',
        'evidencias_exigidas': (
            'Documento de controle de acesso físico e lógico; '
            'revisão anual sob controle da equipe de segurança cibernética; '
            'regras de firewall presentes; '
            'segregação TI/TA; '
            'sem senhas padrão.'
        ),
        'regras_especiais': (
            'Para nota 4 (Excelente): deve estar definido e controlado sob conhecimento do time de '
            'segurança cibernética, com regras de firewall presentes, segregação TI/TA e sem senhas padrão.'
        ),
        'niveis': {
            0: 'Não tem prática: Não existem procedimentos.',
            1: (
                'Iniciando: Documento de controle de acesso físico à sala onde estão os equipamentos. '
                'Quem está autorizado.'
            ),
            2: (
                'Regular: Existe um documento de controle de acesso físico e lógico definido.'
            ),
            3: (
                'Bom: Documento estabelecido e revisado anualmente, sob controle da equipe de segurança '
                'cibernética (revisão de registro de entrada/saída lógica).'
            ),
            4: (
                'Excelente: Definido, controlado e sob conhecimento do time de segurança cibernética. '
                'Regras de firewall presentes, segregação TI/TA, sem senhas padrão.'
            )
        },
        'armadilhas': (
            'Controle de acesso físico sem registro formal = não atinge nota 3. Revisão anual não documentada = nota reduzida. Acesso lógico sem restrição por perfil/cargo = não atinge nota 4.'
        )
    },

    (9, 6): {
        'pratica': '9 – CYBERSEGURANÇA',
        'subitem': '9.7 – Gerenciamento de mídias removíveis (USB)',
        'descricao': 'Evidência: Gerenciamento de mídias removíveis (USB)',
        'evidencias_exigidas': (
            'Comprovação de armazenamento em sala trancada com acesso controlado; '
            'sistema digital de controle de acesso; '
            'logs de acesso revisados periodicamente; '
            'evidência de dispositivos catalogados separadamente.'
        ),
        'regras_especiais': (
            'Para nota 4 (Excelente): sala trancada digitalmente, acesso controlado via sistema, '
            'dispositivos evidenciados separadamente e logs de acesso revisados periodicamente. '
            'Mídias disponíveis para qualquer usuário sem critério = nota 0.'
        ),
        'niveis': {
            0: (
                'Não tem prática: Mídias ficam disponíveis para qualquer usuário acessar sem critério '
                'de acesso.'
            ),
            1: (
                'Iniciando: Armazenadas em sala trancada. '
                'Mais de 5 pessoas autorizadas possuem a chave.'
            ),
            2: (
                'Regular: Armazenadas em sala trancada. '
                '1 ou 2 pessoas autorizadas possuem a chave.'
            ),
            3: (
                'Bom: Armazenadas em sala trancada por mecanismos digitais e acesso controlado via sistema.'
            ),
            4: (
                'Excelente: Sala trancada digitalmente, acesso controlado via sistema, dispositivos '
                'evidenciados separadamente. Logs de acesso revisados periodicamente.'
            )
        },
        'armadilhas': (
            'USB sem controle de entrada/saída em sistema digital = não atinge nota 4. Sala sem tranca física ou digital = não atinge nota 3. Mídia removível sem escaneamento antivírus documentado = nota reduzida.'
        )
    },
}


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================

def get_criterio(pratica_num: int, subitem_idx: int) -> dict:
    """Retorna o critério para uma prática e sub-item específicos."""
    return CRITERIOS.get((pratica_num, subitem_idx), {})


def get_niveis_texto(pratica_num: int, subitem_idx: int) -> dict:
    """Retorna apenas os textos dos níveis para um sub-item."""
    criterio = get_criterio(pratica_num, subitem_idx)
    return criterio.get('niveis', {})


def listar_todos_criterios() -> list:
    """Retorna lista de todos os critérios com campos principais."""
    resultado = []
    for (p, s), criterio in sorted(CRITERIOS.items()):
        resultado.append({
            'key': (p, s),
            'pratica': criterio['pratica'],
            'subitem': criterio['subitem'],
            'descricao': criterio['descricao'],
            'evidencias_exigidas': criterio['evidencias_exigidas'],
            'regras_especiais': criterio['regras_especiais'],
            'niveis': criterio['niveis']
        })
    return resultado
