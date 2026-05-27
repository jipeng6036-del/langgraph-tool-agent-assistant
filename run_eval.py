import json
from datetime import datetime
from pathlib import Path

from agent import run_agent


EVAL_CASES_FILE = Path("eval_cases.json")
EVAL_RESULTS_FILE = Path("eval_results.md")


def load_eval_cases() -> list[dict]:
    """
    读取自动化评测用例。
    """
    with EVAL_CASES_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def run_eval_case(case: dict) -> dict:
    """
    运行单条评测用例，并对比关键状态字段。
    """
    state = run_agent(case["input"])

    actual_tool_action = state["tool_action"]
    actual_error_type = state["error_type"]
    actual_need_confirmation = state["need_confirmation"]

    passed = (
        actual_tool_action == case["expected_tool_action"]
        and actual_error_type == case["expected_error_type"]
        and actual_need_confirmation == case["expected_need_confirmation"]
    )

    return {
        "id": case["id"],
        "input": case["input"],
        "expected_tool_action": case["expected_tool_action"],
        "actual_tool_action": actual_tool_action,
        "expected_error_type": case["expected_error_type"],
        "actual_error_type": actual_error_type,
        "expected_need_confirmation": case["expected_need_confirmation"],
        "actual_need_confirmation": actual_need_confirmation,
        "review_passed": state["review_passed"],
        "passed": passed
    }


def write_eval_results(results: list[dict]) -> None:
    """
    将评测结果写入 Markdown 报告。
    """
    passed_count = sum(1 for result in results if result["passed"])
    total_count = len(results)
    pass_rate = passed_count / total_count if total_count else 0

    lines = [
        "# Tool Agent 自动化评测结果",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"通过率：{passed_count}/{total_count}（{pass_rate:.0%}）",
        "",
        "| id | 输入 | 预期 tool_action | 实际 tool_action | 预期 error_type | 实际 error_type | 预期 need_confirmation | 实际 need_confirmation | review_passed | 是否通过 |",
        "|---|---|---|---|---|---|---|---|---|---|"
    ]

    for result in results:
        lines.append(
            "| {id} | {input} | {expected_tool_action} | {actual_tool_action} | "
            "{expected_error_type} | {actual_error_type} | {expected_need_confirmation} | "
            "{actual_need_confirmation} | {review_passed} | {passed} |".format(
                id=result["id"],
                input=result["input"],
                expected_tool_action=result["expected_tool_action"],
                actual_tool_action=result["actual_tool_action"],
                expected_error_type=result["expected_error_type"],
                actual_error_type=result["actual_error_type"],
                expected_need_confirmation=result["expected_need_confirmation"],
                actual_need_confirmation=result["actual_need_confirmation"],
                review_passed=result["review_passed"],
                passed="通过" if result["passed"] else "不通过"
            )
        )

    EVAL_RESULTS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    cases = load_eval_cases()
    results = [run_eval_case(case) for case in cases]
    write_eval_results(results)

    passed_count = sum(1 for result in results if result["passed"])
    total_count = len(results)
    pass_rate = passed_count / total_count if total_count else 0

    print(f"评测完成：{passed_count}/{total_count} 通过，通过率 {pass_rate:.0%}")
    print(f"结果已写入：{EVAL_RESULTS_FILE}")


if __name__ == "__main__":
    main()
