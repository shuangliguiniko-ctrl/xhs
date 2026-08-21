# MediaCrawler 外部依赖

XHS Research 已内置 MediaCrawler 调用适配器、数据定位、解析、标准化、续采和失败记录能力，但不包含 MediaCrawler 源码。

MediaCrawler 当前使用 `NON-COMMERCIAL LEARNING LICENSE 1.1`，授权限定为非商业学习，并写明授权不可转让。使用者应自行获取项目、完整阅读并接受许可证，同时遵守平台条款、访问控制和适用法律：

- 官方仓库：<https://github.com/NanmiCoder/MediaCrawler>
- 官方许可证：<https://github.com/NanmiCoder/MediaCrawler/blob/main/LICENSE>

在项目 YAML 中配置：

```yaml
crawler:
  adapter: mediacrawler
  mediacrawler_path: /你的/MediaCrawler
```

验证外部安装：

```bash
python3 scripts/verify_skill.py \
  --skill-dir /安装位置/new-xhs-research \
  --mediacrawler /你的/MediaCrawler
```

登录或验证需要人工处理时必须暂停并交还用户操作。不得设计或尝试绕过机制。若 MediaCrawler 不可用，`import`、`mock` 和授权浏览器数据导入流程仍可运行。
