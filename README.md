# TP1 ALG1 TOMÁS MOREIRA

App local em Python para simular entregadores em Belo Horizonte e
encontrar os que estão mais próximos de restaurantes e bares. A interface usa
HTML, CSS e JavaScript servidos por um pequeno servidor Python em `localhost`;
o mapa desenha a malha viária GraphML local e não usa tiles, CDNs ou serviços
web externos.

## Requisitos

- Python 3.10 ou superior
- Windows, macOS ou Linux com um navegador
- Dependências Python instaladas
- CSV original em `data/raw/20261001_atividade_economica.csv`
- Grafo local em `data/roads/bh.graphml`

## Preparar para uso offline

É necessário ter internet **uma vez, durante a preparação**, para obter a rede
de ruas do OpenStreetMap. Depois que o CSV processado e o arquivo GraphML
estiverem preparados, a aplicação não faz requisições de rede.

No PowerShell, dentro da pasta do projeto:

```powershell
python -m venv .venv
python -m pip install -r requirements.txt
```

Ao carregar um grafo, o sistema exclui automaticamente vias para pedestres,
ciclovias, escadarias e acessos explicitamente privados ou não motorizados da
etapa de posicionamento.

## Executar

```powershell
python -m dashboard.app
```

A tela contém os campos de quantidade da frota, busca por estabelecimento e
raio; os resultados aparecem ao lado do mapa vetorial local. Se o grafo estiver
ausente, a tela informa o arquivo que precisa ser preparado. A geração não
substitui ruas por posições fictícias.

O comando inicia um servidor apenas em `127.0.0.1` e abre a página no navegador.
Use a roda do mouse ou os botões `+`/`−` para aplicar zoom no mapa, arraste-o
para navegar e clique em Enquadrar para restaurar a visualização inicial.
A página se adapta ao tamanho do navegador; a tabela de resultados tem rolagem.
Encerre com `Ctrl+C` no terminal onde o comando foi iniciado.
O dashboard não carrega bibliotecas, fontes, tiles ou imagens de terceiros: os
arquivos de interface e os dados do mapa são servidos pelo próprio computador.

## Uso

1. Informe a quantidade de entregadores e clique em Gerar nova frota. Cada
   posição é sorteada por distribuição normal em torno dos estabelecimentos,
   distribuída equitativamente entre os centros e ajustada ao nó de rua mais
   próximo do grafo local do OpenStreetMap.
2. Digite nome, rua ou bairro e selecione um estabelecimento na lista.
3. Escolha o raio e clique em Buscar entregadores próximos.
4. Consulte os pontos em destaque, a distância, o ETA aproximado e o tempo da
   busca.

O ETA é ilustrativo: distância em linha reta dividida por velocidade média
assumida de 20 km/h, não um cálculo de rota viária. O mapa desenha a geometria
das vias armazenada no GraphML; não usa tiles de mapas online.

## Estrutura

```text
dashboard/
  app.py                    Servidor HTTP local e API da interface
  service.py                Busca, simulação e preparação do mapa para o navegador
  web/
    index.html              Estrutura da interface
    style.css               Estilos locais
    app.js                  Interação da página e mapa Canvas
src/
  data.py                   Leitura e preparação dos estabelecimentos
  geohash.py                Codificação, decodificação e cobertura Geohash
  models.py                 Modelos de restaurantes e entregadores
  simulation.py             Frota sintética e encaixe nas ruas locais
  spatial_index.py          Haversine e busca por raio
  trie.py                   Trie radix compacta
data/
  raw/                      CSV original e documentação
  processed/                CSV filtrado e convertido para coordenadas
  roads/                    Grafo GraphML e atribuição do OpenStreetMap
scripts/
  prepare_data.py           Gera o CSV processado
  download_road_graph.py    Baixa o grafo para uso offline
tests/                      Testes dos algoritmos e carregamento local
```

Durante a execução, o navegador troca dados apenas com o servidor local. A
geometria de vias é enviada uma vez, compactada com gzip, e desenhada em Canvas;
zoom, arraste e atualização de marcadores são processados no navegador.

## Estruturas e complexidade

- Cada entregador é indexado por Geohash de até oito caracteres na Trie radix.
- A busca consulta prefixos que cobrem a caixa envolvente do raio, remove
  duplicatas e aplica a distância de Haversine. Os resultados são ordenados por
  distância.
- A interface mostra o tempo observado com `time.perf_counter()`. O resultado
  depende da frota e do computador.

## Testes

```powershell
python -m unittest discover -s tests -v
```
