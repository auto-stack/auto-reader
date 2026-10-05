# 迁移与中断 fixture 说明

- library.json.v0legacy：v0 旧形索引（version 缺失、字段名不同）。
  预期行为：库加载拒绝该文件且保留原件（人工迁移），不静默清空。
  驱动：t04_library_spec.as（S1）。
- 导入中断（孤儿状态）由驱动在临时数据目录构造：
  a) 受管副本已写、索引未写 → 同文件再次导入应完成且复用副本（S3）。
  b) 记录在、受管副本被外删 → 读取返回内容缺失占位，不伪造内容（S4）。
- 10MiB 长文：t04_http_verify.py 现场生成 long-novel.txt（约 10MiB）。
