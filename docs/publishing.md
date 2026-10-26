# SDK 的 PyPI 发布步骤

PyPI 发布包为纯 Python SDK，只包含编解码 API、数据模型、命令行和类型标记。卡图、GUI、展示文案位于 `demo/`，只用于独立 EXE 演示，不进入 SDK wheel 或源码发行包。

## 首次配置（维护者完成一次）

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

首次成功上传会创建 PyPI 项目。Pending Publisher 本身不预留包名，包名最终以成功上传时为准。当前 `v0.1.0a2` Release 早于该工作流，首次应手动选择 `main`，不要选择旧标签构建。

## 使用方安装与依赖

**以下命令在首次 PyPI 发布完成后可用；当前不能把“已准备发布”当成“已上传成功”。**

```bash
python -m pip install --pre czn-deckcode
python -m pip install --upgrade --pre czn-deckcode
```

实验版本也可精确依赖：

```toml
[project]
dependencies = ["czn-deckcode==0.1.0a2"]
```

或者在 `requirements.txt` 中填写 `czn-deckcode==0.1.0a2`。安装后使用 `from czn_deckcode import encode, decode`，无需获取游戏资源。

## 修复 bug 后发布更新

1. 修改代码、运行测试。
2. 同步修改 `pyproject.toml` 和 `src/czn_deckcode/__init__.py` 中的版本，例如 `0.1.0a2` → `0.1.0a3`。
3. 提交代码，为该提交创建新标签 `v0.1.0a3` 并发布对应 GitHub Release；工作流自动构建、安装验证并上传到 PyPI。也可以手动运行工作流，明确选择该标签。
4. 使用方通过 `pip install --upgrade --pre czn-deckcode` 升级；固定了精确版本的项目需修改依赖版本。

PyPI 不允许覆盖已经使用过的发行文件名，删除后也不能复用。不能沿用 GitHub 覆盖同版本附件的做法，修复后应增加版本号。使用方安装的包不会在后台自动更新。

## 发布前的本地验证

```bash
python -m pip install build twine
python -m build --outdir dist/pypi
python -m twine check dist/pypi/*
python -m pip install --no-deps --force-reinstall dist/pypi/czn_deckcode-0.1.0a2-py3-none-any.whl
python -I scripts/check_sdk_install.py
```

应在独立测试环境安装 wheel。验证会检查零运行时依赖、SDK 文件边界、7 条官方码和编解码期间的禁止网络访问条件。

参考：[PyPI 首次可信发布](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)、[GitHub Actions 发布](https://docs.pypi.org/trusted-publishers/using-a-publisher/)、[文件名不可复用](https://docs.pypi.org/publishing/troubleshooting/)。
