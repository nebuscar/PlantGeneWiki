#!/bin/bash
# PGCP 补全下载脚本 - 使用 curl 批量下载

OUTPUT_DIR="/DATA/data2/downloads/PGCP"
cd "$OUTPUT_DIR" || exit 1

URL="https://biobigdata.nju.edu.cn/pgdatabaseAPI/download"

# 批次1
echo "=== 批次 1/14 ==="
curl -L -X POST -H 'Content-Type: application/json' \
  -d '{"files":"actinidia_chinensis.pep.fa.gz;actinidia_chinensis.repeat.gff.gz;actinidia_eriantha.cds.fa.gz;actinidia_eriantha.genomic.fa.gz;actinidia_eriantha.genomic.gff.gz;actinidia_eriantha.pep.fa.gz;actinidia_eriantha.repeat.gff.gz;adiantum_capillus_veneris.cds.fa.gz;adiantum_capillus_veneris.genomic.fa.gz;adiantum_capillus_veneris.genomic.gff.gz;adiantum_capillus_veneris.longest.gff.gz;adiantum_capillus_veneris.pep.fa.gz;adiantum_nelumboides.cds.fa.gz;adiantum_nelumboides.genomic.fa.gz;adiantum_nelumboides.genomic.gff.gz;adiantum_nelumboides.longest.gff.gz;adiantum_nelumboides.pep.fa.gz;aegiceras_corniculatum.cds.fa.gz;aegiceras_corniculatum.genomic.fa.gz;aegiceras_corniculatum.genomic.gff.gz"}' \
  -OJ

sleep 5

# 批次2
echo "=== 批次 2/14 ==="
curl -L -X POST -H 'Content-Type: application/json' \
  -d '{"files":"aegiceras_corniculatum.interpro.gff.gz;aegiceras_corniculatum.longest.gff.gz;aegiceras_corniculatum.pep.fa.gz;aegiceras_corniculatum.repeat.gff.gz;aegilops_bicornis.cds.fa.gz;aegilops_bicornis.genomic.fa.gz;aegilops_bicornis.genomic.gff.gz;aegilops_bicornis.longest.gff.gz;aegilops_bicornis.pep.fa.gz;aegilops_longissima.cds.fa.gz;aegilops_longissima.genomic.fa.gz;aegilops_longissima.genomic.gff.gz;aegilops_longissima.longest.gff.gz;aegilops_longissima.pep.fa.gz;aegilops_searsii.cds.fa.gz;aegilops_searsii.genomic.fa.gz;aegilops_searsii.genomic.gff.gz;aegilops_searsii.longest.gff.gz;aegilops_searsii.pep.fa.gz;aegilops_sharonensis.cds.fa.gz"}' \
  -OJ

sleep 5

# 批次3
echo "=== 批次 3/14 ==="
curl -L -X POST -H 'Content-Type: application/json' \
  -d '{"files":"aegilops_sharonensis.genomic.fa.gz;aegilops_sharonensis.genomic.gff.gz;aegilops_sharonensis.longest.gff.gz;aegilops_sharonensis.pep.fa.gz;aegilops_speltoides.cds.fa.gz;aegilops_speltoides.genomic.fa.gz;aegilops_speltoides.genomic.gff.gz;aegilops_speltoides.longest.gff.gz;aegilops_speltoides.pep.fa.gz;aegilops_tauschii.cds.fa.gz;aegilops_tauschii.genomic.fa.gz;aegilops_tauschii.genomic.gff.gz;aegilops_tauschii.interpro.gff.gz;aegilops_tauschii.longest.gff.gz;aegilops_tauschii.pep.fa.gz;aegilops_tauschii.repeat.gff.gz;aerobryopsis_subdivergens.cds.fa.gz;aerobryopsis_subdivergens.genomic.fa.gz;aerobryopsis_subdivergens.genomic.gff.gz;aerobryopsis_subdivergens.interpro.gff.gz"}' \
  -OJ

sleep 5

# 批次4
echo "=== 批次 4/14 ==="
curl -L -X POST -H 'Content-Type: application/json' \
  -d '{"files":"aldrovanda_vesiculosa.pep.fa.gz;aldrovanda_vesiculosa.repeat.gff.gz;allium_cepa.cds.fa.gz;allium_cepa.genomic.fa.gz;allium_cepa.genomic.gff.gz;allium_cepa.pep.fa.gz;allium_sativum.cds.fa.gz;allium_sativum.genomic.fa.gz;allium_sativum.genomic.gff.gz;allium_sativum.pep.fa.gz;alnus_glutinosa.cds.fa.gz;alnus_glutinosa.genomic.fa.gz;alnus_glutinosa.genomic.gff.gz;alnus_glutinosa.interpro.gff.gz;alnus_glutinosa.pep.fa.gz;alnus_glutinosa.repeat.gff.gz;amaranthus_cruentus.cds.fa.gz;amaranthus_cruentus.genomic.fa.gz;amaranthus_cruentus.genomic.gff.gz;amaranthus_cruentus.interpro.gff.gz"}' \
  -OJ

sleep 5

# 批次5
echo "=== 批次 5/14 ==="
curl -L -X POST -H 'Content-Type: application/json' \
  -d '{"files":"anthoceros_angustus.genomic.fa.gz;anthoceros_angustus.genomic.gff.gz;anthoceros_angustus.pep.fa.gz;anthoceros_angustus.repeat.gff.gz;anthoceros_punctatus.cds.fa.gz;anthoceros_punctatus.genomic.fa.gz;anthoceros_punctatus.genomic.gff.gz;anthoceros_punctatus.interpro.gff.gz;anthoceros_punctatus.longest.gff.gz;anthoceros_punctatus.pep.fa.gz;anthoceros_punctatus.repeat.gff.gz;apium_graveolens.cds.fa.gz;apium_graveolens.genomic.fa.gz;apium_graveolens.genomic.gff.gz;apium_graveolens.longest.gff.gz;apium_graveolens.pep.fa.gz;apium_graveolens.repeat.gff.gz;apostasia_shenzhenica.cds.fa.gz;apostasia_shenzhenica.genomic.fa.gz;apostasia_shenzhenica.genomic.gff.gz"}' \
  -OJ

sleep 5

# 批次6
echo "=== 批次 6/14 ==="
curl -L -X POST -H 'Content-Type: application/json' \
  -d '{"files":"arabidopsis_thaliana.genomic.gff.gz;arabidopsis_thaliana.interpro.gff.gz;arabidopsis_thaliana.longest.gff.gz;arabidopsis_thaliana.miRNA.gff.gz;arabidopsis_thaliana.pep.fa.gz;arabidopsis_thaliana.repeat.gff.gz;arabis_alpina.cds.fa.gz;arabis_alpina.genomic.fa.gz;arabis_alpina.genomic.gff.gz;arabis_alpina.pep.fa.gz;arabis_alpina.repeat.gff.gz;arachis_duranensis.cds.fa.gz;arachis_duranensis.genomic.fa.gz;arachis_duranensis.genomic.gff.gz;arachis_duranensis.interpro.gff.gz;arachis_duranensis.pep.fa.gz;arachis_duranensis.repeat.gff.gz;arachis_hypogaea.cds.fa.gz;arachis_hypogaea.genomic.fa.gz;arachis_hypogaea.genomic.gff.gz"}' \
  -OJ

sleep 5

# 批次7
echo "=== 批次 7/14 ==="
curl -L -X POST -H 'Content-Type: application/json' \
  -d '{"files":"arachis_hypogaea.interpro.gff.gz;arachis_hypogaea.longest.gff.gz;arachis_hypogaea.pep.fa.gz;arachis_hypogaea.repeat.gff.gz;arachis_ipaensis.cds.fa.gz;arachis_ipaensis.genomic.fa.gz;arachis_ipaensis.genomic.gff.gz;arachis_ipaensis.interpro.gff.gz;arachis_ipaensis.pep.fa.gz;arachis_ipaensis.repeat.gff.gz;archidium_alternifolium.cds.fa.gz;archidium_alternifolium.genomic.fa.gz;archidium_alternifolium.genomic.gff.gz;archidium_alternifolium.pep.fa.gz;archidium_alternifolium.repeat.gff.gz;areca_catechu.cds.fa.gz;areca_catechu.genomic.fa.gz;areca_catechu.genomic.gff.gz;areca_catechu.interpro.gff.gz;areca_catechu.pep.fa.gz"}' \
  -OJ

sleep 5

# 批次8
echo "=== 批次 8/14 ==="
curl -L -X POST -H 'Content-Type: application/json' \
  -d '{"files":"aulacomnium_turgidum.cds.fa.gz;aulacomnium_turgidum.genomic.fa.gz;aulacomnium_turgidum.genomic.gff.gz;aulacomnium_turgidum.interpro.gff.gz;aulacomnium_turgidum.pep.fa.gz;aulacomnium_turgidum.repeat.gff.gz;avena_atlantica.genomic.gff.gz;avena_atlantica.interpro.gff.gz;avena_atlantica.longest.gff.gz;avena_atlantica.pep.fa.gz;avena_atlantica.repeat.gff.gz;avena_eriantha.cds.fa.gz;avena_eriantha.genomic.fa.gz;avena_eriantha.genomic.gff.gz;avena_eriantha.interpro.gff.gz;avena_eriantha.longest.gff.gz;avena_eriantha.pep.fa.gz;avena_eriantha.repeat.gff.gz;averrhoa_carambola.cds.fa.gz;averrhoa_carambola.genomic.fa.gz"}' \
  -OJ

sleep 5

# 批次9
echo "=== 批次 9/14 ==="
curl -L -X POST -H 'Content-Type: application/json' \
  -d '{"files":"averrhoa_carambola.genomic.gff.gz;averrhoa_carambola.interpro.gff.gz;averrhoa_carambola.longest.gff.gz;averrhoa_carambola.pep.fa.gz;averrhoa_carambola.repeat.gff.gz;azolla_filiculoides.cds.fa.gz;bryum_knowltonii.cds.fa.gz;bryum_knowltonii.genomic.fa.gz;bryum_knowltonii.genomic.gff.gz;bryum_knowltonii.interpro.gff.gz;bryum_knowltonii.pep.fa.gz;bryum_knowltonii.repeat.gff.gz;cajanus_cajan.repeat.gff.gz;calamus_simplicifolius.cds.fa.gz;calamus_simplicifolius.genomic.fa.gz;calamus_simplicifolius.genomic.gff.gz;calamus_simplicifolius.interpro.gff.gz;calamus_simplicifolius.pep.fa.gz;calamus_simplicifolius.repeat.gff.gz;callicarpa_americana.cds.fa.gz"}' \
  -OJ

sleep 5

# 批次10
echo "=== 批次 10/14 ==="
curl -L -X POST -H 'Content-Type: application/json' \
  -d '{"files":"callicarpa_americana.genomic.fa.gz;callicarpa_americana.genomic.gff.gz;callicarpa_americana.pep.fa.gz;callicarpa_americana.repeat.gff.gz;calliergon_cordifolium.cds.fa.gz;calliergon_cordifolium.genomic.fa.gz;calliergon_cordifolium.genomic.gff.gz;calliergon_cordifolium.interpro.gff.gz;calliergon_cordifolium.pep.fa.gz;calliergon_cordifolium.repeat.gff.gz;calliergonella_cuspidata.cds.fa.gz;calliergonella_cuspidata.genomic.fa.gz;camelina_sativa.longest.gff.gz;camelina_sativa.pep.fa.gz;camelina_sativa.repeat.gff.gz;camellia_chekiangoleosa.cds.fa.gz;camellia_chekiangoleosa.genomic.fa.gz;camellia_chekiangoleosa.genomic.gff.gz;camellia_chekiangoleosa.longest.gff.gz;camellia_chekiangoleosa.pep.fa.gz"}' \
  -OJ

sleep 5

# 批次11
echo "=== 批次 11/14 ==="
curl -L -X POST -H 'Content-Type: application/json' \
  -d '{"files":"camellia_fluviatilis.cds.fa.gz;camellia_fluviatilis.genomic.fa.gz;camellia_fluviatilis.genomic.gff.gz;camellia_fluviatilis.longest.gff.gz;camellia_fluviatilis.pep.fa.gz;camptotheca_acuminata.cds.fa.gz;camptotheca_acuminata.genomic.fa.gz;camptotheca_acuminata.genomic.gff.gz;camptotheca_acuminata.interpro.gff.gz;camptotheca_acuminata.longest.gff.gz;camptotheca_acuminata.pep.fa.gz;camptotheca_acuminata.repeat.gff.gz;chlamydomonas_sp_ICE.longest.gff.gz;chlamydomonas_sp_ICE.pep.fa.gz;chloranthus_sessilifolius.cds.fa.gz;chloranthus_sessilifolius.genomic.fa.gz;chloranthus_sessilifolius.genomic.gff.gz;chloranthus_sessilifolius.interpro.gff.gz;chloranthus_sessilifolius.longest.gff.gz;chloranthus_sessilifolius.pep.fa.gz"}' \
  -OJ

sleep 5

# 批次12
echo "=== 批次 12/14 ==="
curl -L -X POST -H 'Content-Type: application/json' \
  -d '{"files":"chloranthus_sessilifolius.repeat.gff.gz;chloranthus_spicatus.cds.fa.gz;chloranthus_spicatus.genomic.fa.gz;chloranthus_spicatus.genomic.gff.gz;chloranthus_spicatus.longest.gff.gz;chloranthus_spicatus.pep.fa.gz;chlorella_sorokiniana.cds.fa.gz;chlorella_sorokiniana.genomic.fa.gz;chlorella_sorokiniana.genomic.gff.gz;chlorella_sorokiniana.longest.gff.gz;chlorella_sorokiniana.pep.fa.gz;chlorella_variabilis.cds.fa.gz;chorisodontium_acidophyllum.cds.fa.gz;chorisodontium_acidophyllum.genomic.fa.gz;chorisodontium_acidophyllum.genomic.gff.gz;chorisodontium_acidophyllum.interpro.gff.gz;chorisodontium_acidophyllum.pep.fa.gz;chorisodontium_acidophyllum.repeat.gff.gz;chromochloris_zofingiensis.longest.gff.gz;chromochloris_zofingiensis.pep.fa.gz"}' \
  -OJ

sleep 5

# 批次13
echo "=== 批次 13/14 ==="
curl -L -X POST -H 'Content-Type: application/json' \
  -d '{"files":"chromochloris_zofingiensis.repeat.gff.gz;chrysanthemum_nankingense.cds.fa.gz;chrysanthemum_nankingense.genomic.fa.gz;chrysanthemum_nankingense.genomic.gff.gz;chrysanthemum_nankingense.interpro.gff.gz;chrysanthemum_nankingense.longest.gff.gz;chrysanthemum_nankingense.pep.fa.gz;chrysanthemum_nankingense.repeat.gff.gz;chrysanthemum_seticuspe.cds.fa.gz;chrysanthemum_seticuspe.genomic.fa.gz;chrysanthemum_seticuspe.genomic.gff.gz;chrysanthemum_seticuspe.interpro.gff.gz;chrysanthemum_seticuspe.pep.fa.gz;chrysanthemum_seticuspe.repeat.gff.gz;cicer_arietinum.cds.fa.gz;cicer_arietinum.genomic.fa.gz;cicer_arietinum.genomic.gff.gz;cicer_arietinum.interpro.gff.gz;polytrichastrum_alpinum.cds.fa.gz;polytrichastrum_alpinum.genomic.fa.gz"}' \
  -OJ

sleep 5

# 批次14
echo "=== 批次 14/14 ==="
curl -L -X POST -H 'Content-Type: application/json' \
  -d '{"files":"polytrichastrum_alpinum.genomic.gff.gz;polytrichastrum_alpinum.interpro.gff.gz;polytrichastrum_alpinum.pep.fa.gz;polytrichastrum_alpinum.repeat.gff.gz;syntrichia_ruralis.cds.fa.gz;syntrichia_ruralis.genomic.fa.gz;syntrichia_ruralis.genomic.gff.gz;syntrichia_ruralis.interpro.gff.gz;syntrichia_ruralis.pep.fa.gz;syntrichia_ruralis.repeat.gff.gz"}' \
  -OJ

echo "=== 全部完成 ==="