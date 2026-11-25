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

## 手机适配

`site/mobile.css`为iPhone 15等手机提供单列题库、较大的字体及触控区域、句内填空与词块换行、Safari输入字号、安全区边距和播放器底部留白。覆盖竖屏及触屏设备的横屏短视口，保留双指缩放。样式与桌面页面分开加载。

## 全量题库（2026-11-26）

已导入 Wofo 70 个试卷定义：完整模考 Mock 1–50、口语 Mock 1–70、写作 Mock 1–70，合计 5,110 条题组、6,460 小题。口语和写作入口包含完整模考中的对应科目，题目共用相同 ID 和学习进度，不重复计数。原有 2,320 条题组 ID 全部保留。

范围为原站正常试卷定义返回的默认组合；不包含需由考试作答触发的其他自适应分支。Mock 20 的 `mock-20__45a7f30ed861` 原站答案指向缺失的第四个选项，保留题面，暂不自动评分。

重建题库（Python 3；下载媒体检查需要 ffprobe）：

```sh
python3 scripts/fetch_wofo.py
python3 scripts/import_wofo.py .import-runtime/source/raw.json
python3 scripts/cache_media.py
python3 verify_site.py
```

原始下载及检查报告保存在被 Git 忽略的 `.import-runtime/`，不会随网站发布。
