# SDK 的 PyPI 发布步骤

PyPI 发布包为纯 Python SDK，只包含编解码 API、数据模型、命令行和类型标记。卡图、GUI、展示文案位于 `demo/`，只用于独立 EXE 演示，不进入 SDK wheel 或源码发行包。

## 日常更新发布

本项目已完成 PyPI 首次发布，并配置 GitHub Actions Trusted Publishing。维护者准备新版本并发布 GitHub Release 后，由工作流打包、检查和上传 SDK，无需在本地手工上传 wheel 或配置长期 API Token。

1. 修改代码并运行测试。如果改动涉及 SDK 功能或修复，需要发布新的 PyPI 版本；只改 Demo 或仓库中未打进 SDK 的文档时，不必单独更新 PyPI。
2. 同步修改 `pyproject.toml` 和 `src/czn_deckcode/__init__.py` 的版本。本次为 `0.1.0a3`，下一次可使用尚未发布过的 `0.1.0a4`。同步更新发布说明与依赖示例。
3. 提交并推送代码，等待 [Test and package](https://github.com/liuzihua699/czn-deckcode/actions/workflows/build.yml) 测试和打包通过，为该提交创建对应的新标签，例如 `v0.1.0a3`。
4. 发布该标签的 GitHub Release。`Publish SDK to PyPI` 工作流会自动构建 wheel 和源码发行包、检查 SDK 文件边界及安装结果，再使用可信发布上传到 PyPI。仅推送代码或创建 tag 不会触发 PyPI 上传。
5. 确认 [发布工作流](https://github.com/liuzihua699/czn-deckcode/actions/workflows/publish-pypi.yml) 成功，并检查 [PyPI 项目页](https://pypi.org/project/czn-deckcode/) 已显示新版本。Windows Demo 的 ZIP／EXE 作为独立附件上传到 GitHub Release。

Windows 大附件可通过 [Upload desktop release assets](https://github.com/liuzihua699/czn-deckcode/actions/workflows/release-desktop-assets.yml) 上传：输入现有 Release 标签及对应的成功构建运行 ID。工作流校验构建提交与标签一致、文件校验值和 EXE 离线自测后，从 GitHub 构建机直接上传 ZIP／EXE；它不会发布 PyPI 或替换包含 SDK 文件的总校验清单。

工作流仍可能因构建失败、PyPI 权限或 GitHub 环境审批而中止；应以工作流结果和 PyPI 实际版本为准。需要重试时，可手动运行发布工作流，`ref` 选择该版本标签，并勾选 `publish`。

PyPI 不允许覆盖已经使用过的发行文件名，删除后也不能复用。SDK 代码修复后应增加版本号，不应覆盖同版本附件来代替 PyPI 更新。用户安装的旧包不会自动更新，需要执行下方升级命令；固定了精确版本的项目还需修改依赖版本。

## 首次配置（维护者完成一次）

现有仓库已完成此配置；以下步骤供新仓库或迁移时参考。

1. 在 [PyPI 注册](https://pypi.org/account/register/)，验证邮箱，并按 PyPI 账号页面要求启用双重验证。
2. 登录后打开 [Publishing](https://pypi.org/manage/account/publishing/)，添加新的 GitHub Pending Publisher（项目未创建时使用此入口）。
3. 填写以下值：

| 字段 | 填写内容 |
| --- | --- |
| PyPI Project Name | `czn-deckcode` |
| Owner | `liuzihua699` |
| Repository name | `czn-deckcode` |
| Workflow name | `publish-pypi.yml` |
| Environment name | `pypi` |

GitHub 仓库对应环境名也为 `pypi`。不需要把 PyPI 密码或令牌发送给任何人，不需要配置长期 API Token。

4. 在 GitHub 的 [Publish SDK to PyPI](https://github.com/liuzihua699/czn-deckcode/actions/workflows/publish-pypi.yml) 页面选择 Run workflow，`ref` 填 `main`。不勾选 `publish` 时只构建和验证；完成 PyPI 关联后勾选，才会上传。

首次成功上传会创建 PyPI 项目。Pending Publisher 本身不预留包名，包名最终以成功上传时为准。旧标签 `v0.1.0a2` 早于发布工作流，不用于重新运行可信发布；后续版本使用各自的新标签。

## 使用方安装与依赖

SDK 已完成首次 PyPI 发布，使用方可以直接安装：

```bash
python -m pip install --upgrade --pre --index-url https://pypi.org/simple czn-deckcode
```

实验版本也可精确依赖：

```toml
[project]
dependencies = ["czn-deckcode==0.1.0a3"]
```

或者在 `requirements.txt` 中填写 `czn-deckcode==0.1.0a3`。安装后使用 `from czn_deckcode import encode, decode`，无需获取游戏资源。

## 发布前的本地验证

```bash
python -m pip install build twine
python -m build --outdir dist/pypi
python -m twine check dist/pypi/*
python -m pip install --no-deps --force-reinstall dist/pypi/czn_deckcode-0.1.0a3-py3-none-any.whl
python -I scripts/check_sdk_install.py
```

这里安装本地 wheel 是维护者验证待发布产物的步骤；普通使用方直接从 PyPI 安装即可。应在独立测试环境安装 wheel。验证会检查零运行时依赖、SDK 文件边界、7 条官方码和编解码期间的禁止网络访问条件。

参考：[PyPI 首次可信发布](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)、[GitHub Actions 发布](https://docs.pypi.org/trusted-publishers/using-a-publisher/)、[文件名不可复用](https://docs.pypi.org/publishing/troubleshooting/)。
