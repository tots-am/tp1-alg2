"""Script que eu usei só para converter o arquivo .osm.xz em .graphml, não é necessário para o funcionamento do projeto."""

import lzma
import os
import osmnx as ox

arquivo_osm_xz = "bh.osm.xz"
arquivo_temp_osm = "bh.osm"
arquivo_graphml = "bh.graphml"

try:
    print("Descompactando o arquivo .osm.xz para o disco (modo streaming)...")
    with lzma.open(arquivo_osm_xz, "rb") as f_in:
        with open(arquivo_temp_osm, "wb") as f_out:
            for chunk in iter(lambda: f_in.read(1024 * 1024), b""):  
                f_out.write(chunk)

    print("Construindo o grafo a partir do arquivo XML extraído...")
    G = ox.graph_from_xml(arquivo_temp_osm)

    print("Convertendo e salvando em GraphML...")
    ox.save_graphml(G, filepath=arquivo_graphml)
    print(f"Sucesso! Arquivo salvo em: {arquivo_graphml}")

finally:
    if os.path.exists(arquivo_temp_osm):
        print("Limpando arquivos temporários...")
        os.remove(arquivo_temp_osm)