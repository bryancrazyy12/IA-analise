# Detector de Veracidade de Notícias (URL)

Aplicativo em **Streamlit** que recebe o link de uma notícia e gera um parecer heurístico:

- extrai título e texto da matéria;
- pesquisa cobertura relacionada em outras fontes;
- identifica sinais de **corroboração** e de **desmentido**;
- retorna uma pontuação (0 a 1) e um veredito.

> ⚠️ Importante: o resultado é **assistivo** e não substitui checagem profissional.

## Como rodar

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

Se estiver no Windows (PowerShell), ative o ambiente com:

```powershell
.venv\Scripts\Activate.ps1
```

## Testes

```bash
python3 -m unittest -v
```

## Arquivos principais

- `app.py`: interface do app.
- `verifier.py`: lógica de extração, busca, classificação e score.
- `test_verifier.py`: testes unitários básicos.
