# 托福自习室

静态托福练习网页，包含完整模考、口语/写作专项、L&R频次统计与原音频播放。所有资源使用相对路径，兼容GitHub Pages项目网址。

## 发布

1. 将此目录上传到你的GitHub仓库，默认分支使用`main`。
2. 在仓库Settings → Pages中将Source设为GitHub Actions。
3. `.github/workflows/pages.yml`会部署`site/`目录；后续推送自动更新。

普通GitHub Pages网页公开可访问；源仓库私有不等于网页私有。发布前需确认允许公开题库和媒体，以及具备相应发布权限。

## 本地运行

```sh
python3 -m http.server 4175 --bind 127.0.0.1 --directory site
```

打开http://127.0.0.1:4175/。

学习进度仅保存在浏览器。原本地网址和GitHub Pages网址的进度独立，不自动迁移。仅供个人学习；题目和原媒体来自Wofo，L&R频次来自此前整理材料。
