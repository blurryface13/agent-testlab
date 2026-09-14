# TestLab 测试入口

工作台自身的无模型合同测试位于 `backend/tests/`，由受控 runner 只允许调用已登记的测试文件。真实业务测试按目标和层级继续放在对应目录，不能由浏览器传入任意路径。

本地执行：

```bash
PYTHONPATH=backend python -m pytest backend/tests/test_testing_workbench.py -q
```
