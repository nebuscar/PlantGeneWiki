
# 加载包
library(Biostrings)
library(dplyr)  # 用于数据整理
# 读取FASTA文件（替换为你的文件路径）
fasta_fileaa<-'C:/Users/36278/Documents/WeChat Files/wxid_b29k9bp5c8l922/FileStorage/File/2026-04/ncbi_dataset/ncbi_dataset/data/GCA_043235775.1/protein.faa'
fasta_file <-'C:/Users/36278/Documents/WeChat Files/wxid_b29k9bp5c8l922/FileStorage/File/2026-04/ncbi_dataset/ncbi_dataset/data/GCA_043235775.1/cds_from_genomic.fna'
fasta_data <- readDNAStringSet(fasta_file)  # 蛋白序列用readAAStringSet，DNA用readDNAStringSet#fasta_fileaa<-'C:/Users/36278/Documents/WeChat Files/wxid_b29k9bp5c8l922/FileStorage/File/2026-04/ncbi_dataset/ncbi_dataset/data/GCA_043235775.1/protein.faa'
fasta_dataa<-readAAStringSet(fasta_fileaa)
# 查看基本信息
print(fasta_data)  # 显示序列数量、长度范围等
# 提取序列ID、描述和序列
print(fasta_dataa)

seq_info <- data.frame(
  ID = names(fasta_data),
  Sequence = as.character(fasta_data),
  Length = width(fasta_data)
)
seq_info1 <- data.frame(
  ID = names(fasta_dataa),
  Sequence = as.character(fasta_dataa),
  Length = width(fasta_dataa)
)
head(seq_info$ID,1)
head(seq_info1$ID,1)
id<-sub('_.*','',seq_info$ID)
# 查看前6行数据
data<-data.frame(id,seq_info$Sequence)
# 计算序列字母频率（以第一个序列为例）
setwd('D:/DNA注释文件')
write.csv(data,'DNAzhushi.csv')