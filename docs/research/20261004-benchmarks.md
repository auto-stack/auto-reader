# Auto Reader：业界调研

日期：2026-10-04。首版重点是个人阅读，不引入电子书商店或社交社区。

| 依据 | 核实内容 | 决策 |
|---|---|---|
| [calibre E-book viewer](https://manual.calibre-ebook.com/viewer.html) | 目录导航、文本高亮、搜索、阅读样式、图像及键盘操作 | 常规读书体验必须完整；不以AI摘要替代原文阅读 |
| [Readwise Reader 摘录导出](https://docs.readwise.io/reader/docs/faqs/exporting) | 摘录/笔记 Markdown 导出及其他笔记工具的连接 | 书内摘录可移植、带出处；与Notes/Jade接口解耦 |
| [Readwise Reader 高亮与笔记](https://docs.readwise.io/reader/docs/faqs/highlights-tags-notes) | 键盘阅读、定位原上下文、标签与导出 | 摘录可回到原位置，阅读与知识整理形成闭环 |
| [W3C EPUB 3.3](https://www.w3.org/TR/epub-33/) | EPUB出版物的结构与内容规范 | EPUB导入依据标准和公开fixture，明确重排版子集；不自行发明“EPUB兼容”定义 |

首个里程碑用 TXT/Markdown 完成真实导入/恢复闭环；EPUB 重排版是本轮产品路线的下一项必需能力，不能以 TXT 完成宣称已是完整电子书阅读器。PDF固定版式、扫描OCR、漫画、听书和网站稍后读可独立演进。
