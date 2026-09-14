# Product

## Register

product

## Users

主要使用者是 Dora、Codex 与 Hermes。三者协作维护文生图安全评测：Dora 查看实验与决策，Hermes 运行生成和评测任务，Codex 协助维护 pipeline、分析结果和迭代提示词。

## Product Purpose

为既有的安全评测 pipeline 提供本地控制台。用户应能配置模型通道、查看数据集和任务、比较大类/小类 ASR，并在运行前发现 API 额度风险。首版不重写生成或裁判逻辑，只以稳定的本地接口封装现有输出和运行入口。

### 2026-09-15 扩展定位（设计阶段）

项目更名 Agent TestLab，在既有 T2I 评测模块中加入自动化测试工作台。用户按对象、测试类型、工具与场景选择执行，查看请求、断言、失败证据及工具操作说明。pytest/Requests、Postman/Newman、JMeter 与 Jenkins 承担不同执行职责；科研 Agent 的 Monitor 与 LLM Judge 在 Asteria 侧接入，本工作台汇总结果。完整范围见 spec.md，界面约束见 DESIGN.md；新增功能尚未实现。

## Brand Personality

专业、克制、精致。中文优先，参考 Hermes 与 APIDock 的浅色高信息密度控制台，但不复制其品牌元素。

## Anti-references

避免营销落地页、花哨渐变、无意义的大数字卡片、过度装饰的动效，以及把安全判断伪装成确定事实的文案。

## Design Principles

1. Pipeline first：任务、输入、产物和指标的关系优先于装饰。
2. 可追溯：每个汇总指标都能进入数据集、模型和运行记录。
3. 成本可见：API 额度、单次预计消耗和低成本验证状态始终可见。
4. 谨慎表达：区分生成成功、拒答、裁判命中和未判定。
5. 紧凑而不拥挤：用清晰层级承载实验信息，保留必要留白。

## Accessibility & Inclusion

中文文本和数据状态须具备足够对比度；颜色不作为唯一状态载体；支持键盘焦点；遵守系统“减少动态效果”偏好。
