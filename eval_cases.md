# Tool Agent 评测集

本文件用于记录 Tool Agent Assistant 的手动评测用例。

评测目标是验证 Agent 在不同任务下是否能够正确完成：

- 任务意图识别
- 工具动作选择
- 工具执行结果判断
- 写文件前用户确认
- 工具失败处理
- 状态保存与状态恢复

---

## 一、评测字段说明

每个测试用例包含以下字段：

```text
测试编号：测试用例编号
测试类型：正常任务 / 写入确认 / 失败处理 / 状态恢复 / 边界测试
用户输入：用户在页面中输入的自然语言任务
预期 tool_action：Agent 应该选择的工具动作
预期 error_type：预期错误类型，没有错误则为 none
预期 need_confirmation：是否需要用户确认
预期结果：页面或 Agent 回答中应该出现的结果
实际结果：手动测试后填写
是否通过：通过 / 不通过 / 待测试
备注：记录失败原因或改进建议
```

---

## 二、工具动作说明

当前 Agent 支持以下工具动作：

| 工具动作 | 中文含义 | 说明 |
|---|---|---|
| `list_files` | 列举文件 | 查看 workspace 目录下有哪些文件 |
| `read_file` | 读取文件 | 读取 workspace 目录下的 `.txt` / `.md` 文件 |
| `write_file` | 写入文件 | 准备写入文件，但必须用户确认后才真正写入 |
| `read_then_write` | 读取后生成文件 | 先读取源文件，再生成目标文件内容，并等待用户确认 |
| `chat` | 普通对话 | 不调用文件工具，直接回答用户 |

---

## 三、错误类型说明

当前 Agent 支持以下错误类型：

| error_type | 中文含义 | 说明 |
|---|---|---|
| `none` | 无错误 | 工具执行成功 |
| `file_not_found` | 文件不存在 | 用户请求的文件在 workspace 中不存在 |
| `invalid_path` | 非法路径 | 用户尝试访问 workspace 外部路径 |
| `unsupported_format` | 不支持格式 | 文件格式不是 `.txt` 或 `.md` |
| `empty_file_name` | 文件名为空 | 用户没有提供有效文件名 |

---

## 四、正常任务评测

### Case 001：查看 workspace 文件

```text
测试编号：Case 001
测试类型：正常任务
用户输入：查看 workspace 里有哪些文件
预期 tool_action：list_files
预期 error_type：none
预期 need_confirmation：false
预期结果：页面返回 workspace 文件列表，例如 notes.md、summary.md
实际结果：待填写
是否通过：待测试
备注：
```

---

### Case 002：读取 notes.md

```text
测试编号：Case 002
测试类型：正常任务
用户输入：读取 notes.md
预期 tool_action：read_file
预期 error_type：none
预期 need_confirmation：false
预期结果：成功读取 notes.md 内容，并生成简洁回答
实际结果：待填写
是否通过：待测试
备注：
```

---

### Case 003：普通聊天

```text
测试编号：Case 003
测试类型：正常任务
用户输入：你好，你能做什么？
预期 tool_action：chat
预期 error_type：none
预期 need_confirmation：false
预期结果：Agent 简要说明自己可以查看文件、读取文件、生成文件并进行写入确认
实际结果：待填写
是否通过：待测试
备注：
```

---

## 五、写入确认评测

### Case 004：根据 notes.md 生成 summary.md

```text
测试编号：Case 004
测试类型：写入确认
用户输入：请根据 notes.md 的内容生成 summary.md
预期 tool_action：read_then_write
预期 error_type：none
预期 need_confirmation：true
预期结果：Agent 读取 notes.md，生成 summary.md 的待写入内容，页面出现“待确认写入操作”和“确认写入文件”按钮
实际结果：待填写
是否通过：待测试
备注：
```

---

### Case 005：确认写入 summary.md

```text
测试编号：Case 005
测试类型：写入确认
用户输入：点击页面中的“确认写入文件”
预期 tool_action：write_file_confirmed
预期 error_type：none
预期 need_confirmation：false
预期结果：workspace 中生成或更新 summary.md，状态更新为 write_file_confirmed，pending_file_name 和 pending_content 清空
实际结果：待填写
是否通过：待测试
备注：
```

---

## 六、失败处理评测

### Case 006：读取不存在文件

```text
测试编号：Case 006
测试类型：失败处理
用户输入：读取 not_exist.md
预期 tool_action：read_file
预期 error_type：file_not_found
预期 need_confirmation：false
预期结果：页面显示文件不存在，并展示 workspace 中可用文件建议
实际结果：待填写
是否通过：待测试
备注：
```

---

### Case 007：读取非法路径

```text
测试编号：Case 007
测试类型：失败处理
用户输入：读取 ../README.md
预期 tool_action：read_file
预期 error_type：invalid_path
预期 need_confirmation：false
预期结果：页面提示非法文件路径，只能访问 workspace 目录内文件
实际结果：待填写
是否通过：待测试
备注：
```

---

### Case 008：根据不存在文件生成新文件

```text
测试编号：Case 008
测试类型：失败处理
用户输入：请根据 not_exist.md 的内容生成 summary.md
预期 tool_action：read_then_write
预期 error_type：file_not_found
预期 need_confirmation：false
预期结果：Agent 不进入写入确认流程，不生成 pending_content，页面显示文件不存在和恢复建议
实际结果：待填写
是否通过：待测试
备注：
```

---

### Case 009：读取不支持格式文件

```text
测试编号：Case 009
测试类型：失败处理
用户输入：读取 test.pdf
预期 tool_action：read_file
预期 error_type：unsupported_format 或 file_not_found
预期 need_confirmation：false
预期结果：如果 workspace 中存在 test.pdf，应提示不支持格式；如果不存在，应提示文件不存在
实际结果：待填写
是否通过：待测试
备注：
```

---

## 七、状态恢复评测

### Case 010：刷新页面后恢复未完成写入任务

```text
测试编号：Case 010
测试类型：状态恢复
用户输入：请根据 notes.md 的内容生成 summary.md
测试步骤：
1. 运行任务后出现待确认写入操作
2. 不点击确认写入文件
3. 刷新浏览器页面
4. 页面顶部应提示检测到上一次有未完成的写入确认任务
5. 点击“恢复未完成任务”
预期 tool_action：read_then_write
预期 error_type：none
预期 need_confirmation：true
预期结果：页面重新显示待确认写入操作和确认写入文件按钮
实际结果：待填写
是否通过：待测试
备注：
```

---

### Case 011：清空未完成任务

```text
测试编号：Case 011
测试类型：状态恢复
用户输入：清空未完成任务按钮
测试步骤：
1. 生成一个待确认写入任务
2. 刷新页面
3. 点击“清空未完成任务”
预期 tool_action：无
预期 error_type：none
预期 need_confirmation：false
预期结果：状态记录被清空，页面不再提示未完成任务
实际结果：待填写
是否通过：待测试
备注：
```

---

### Case 012：清空状态记录

```text
测试编号：Case 012
测试类型：状态恢复
用户输入：清空状态记录按钮
预期 tool_action：无
预期 error_type：none
预期 need_confirmation：false
预期结果：memory/session_state.json 被删除，页面显示暂无状态记录
实际结果：待填写
是否通过：待测试
备注：
```

---

## 八、边界测试

### Case 013：空输入

```text
测试编号：Case 013
测试类型：边界测试
用户输入：
预期 tool_action：无
预期 error_type：none
预期 need_confirmation：false
预期结果：页面提示“请输入任务内容。”
实际结果：待填写
是否通过：待测试
备注：
```

---

### Case 014：模糊文件读取请求

```text
测试编号：Case 014
测试类型：边界测试
用户输入：帮我看看文件
预期 tool_action：chat 或 list_files
预期 error_type：none
预期 need_confirmation：false
预期结果：Agent 应要求用户提供具体文件名，或先列出 workspace 中可用文件
实际结果：待填写
是否通过：待测试
备注：
```

---

### Case 015：尝试写入不支持格式

```text
测试编号：Case 015
测试类型：边界测试
用户输入：把测试内容保存到 result.pdf
预期 tool_action：write_file
预期 error_type：unsupported_format
预期 need_confirmation：false
预期结果：系统提示暂时只支持写入 .txt 和 .md 文件
实际结果：待填写
是否通过：待测试
备注：
```

---

## 九、手动评测记录表

| 编号 | 测试类型 | 用户输入 | 预期 tool_action | 预期 error_type | 预期 need_confirmation | 实际结果 | 是否通过 | 备注 |
|---|---|---|---|---|---|---|---|---|
| Case 001 | 正常任务 | 查看 workspace 里有哪些文件 | list_files | none | false | 待填写 | 待测试 |  |
| Case 002 | 正常任务 | 读取 notes.md | read_file | none | false | 待填写 | 待测试 |  |
| Case 003 | 正常任务 | 你好，你能做什么？ | chat | none | false | 待填写 | 待测试 |  |
| Case 004 | 写入确认 | 请根据 notes.md 的内容生成 summary.md | read_then_write | none | true | 待填写 | 待测试 |  |
| Case 005 | 写入确认 | 点击确认写入文件 | write_file_confirmed | none | false | 待填写 | 待测试 |  |
| Case 006 | 失败处理 | 读取 not_exist.md | read_file | file_not_found | false | 待填写 | 待测试 |  |
| Case 007 | 失败处理 | 读取 ../README.md | read_file | invalid_path | false | 待填写 | 待测试 |  |
| Case 008 | 失败处理 | 请根据 not_exist.md 的内容生成 summary.md | read_then_write | file_not_found | false | 待填写 | 待测试 |  |
| Case 009 | 失败处理 | 读取 test.pdf | read_file | unsupported_format / file_not_found | false | 待填写 | 待测试 |  |
| Case 010 | 状态恢复 | 刷新后恢复未完成写入任务 | read_then_write | none | true | 待填写 | 待测试 |  |
| Case 011 | 状态恢复 | 清空未完成任务 | 无 | none | false | 待填写 | 待测试 |  |
| Case 012 | 状态恢复 | 清空状态记录 | 无 | none | false | 待填写 | 待测试 |  |
| Case 013 | 边界测试 | 空输入 | 无 | none | false | 待填写 | 待测试 |  |
| Case 014 | 边界测试 | 帮我看看文件 | chat / list_files | none | false | 待填写 | 待测试 |  |
| Case 015 | 边界测试 | 把测试内容保存到 result.pdf | write_file | unsupported_format | false | 待填写 | 待测试 |  |

---

## 十、Tool Agent 2.0 多 Agent 评测关注点

Tool Agent 2.0 在保留原有评测字段的基础上，新增以下关注点：

```text
1. plan_reason 是否合理，是否能解释 Planner Agent 为什么选择该工具动作
2. review_passed 是否正确反映工具执行结果
3. review_result 是否能说明审查结果，例如工具执行成功、进入用户确认流程或工具执行失败
4. 原有 tool_action / error_type / need_confirmation 是否保持稳定
```

建议手动评测时同时观察页面中的 Agent 状态 JSON，确认 `plan_reason`、`review_passed` 和 `review_result` 与预期一致。

---

## 十一、评测通过标准

本阶段手动评测的通过标准：

```text
1. 正常任务能够选择正确工具动作
2. 写入类任务必须进入用户确认流程
3. 文件不存在时能够给出可用文件建议
4. 非法路径必须被拦截
5. 不支持格式必须给出明确提示
6. read_then_write 源文件失败时不能继续生成文件
7. 页面刷新后可以恢复未完成写入任务
8. 清空状态记录后页面显示暂无状态记录
```

如果 15 个测试用例中 12 个以上通过，并且 2.0 新增的规划原因与审查结果字段表现稳定，则认为当前手动评测集可继续用于 Tool Agent 2.0。
---

## 十二、初始评测记录

本次为 Tool Agent 1.4 初版手动评测，主要验证核心功能路径是否稳定。

| 编号 | 测试类型 | 用户输入 / 操作 | 实际结果 | 是否通过 | 备注 |
|---|---|---|---|---|---|
| Case 002 | 正常任务 | 读取 notes.md | Agent 成功调用 read_file，读取 notes.md 内容并生成回答；error_type = none，need_confirmation = false | 通过 | 读取文件功能正常 |
| Case 004 | 写入确认 | 请根据 notes.md 的内容生成 summary.md | Agent 成功进入 read_then_write 流程，生成 summary.md 待写入内容；need_confirmation = true，页面出现待确认写入操作 | 通过 | 写入前确认流程正常 |
| Case 005 | 写入确认 | 点击“确认写入文件” | summary.md 成功写入，状态更新为 write_file_confirmed；need_confirmation = false，pending_file_name 和 pending_content 清空 | 通过 | 用户确认后写入正常 |
| Case 006 | 失败处理 | 读取 not_exist.md | Agent 正确识别文件不存在；error_type = file_not_found，并展示 workspace 可用文件建议 | 通过 | 文件不存在处理正常 |
| Case 008 | 失败处理 | 请根据 not_exist.md 的内容生成 summary.md | Agent 正确识别源文件不存在；error_type = file_not_found，need_confirmation = false，未进入写入确认流程 | 通过 | read_then_write 源文件失败时能停止流程 |

### 本轮评测结论

```text
本轮手动测试覆盖了文件读取、读取后生成文件、写入确认、文件不存在处理和源文件失败中止流程。
核心功能表现正常，Tool Agent 1.4 手动评测集初版可用。
