from anka.core.agent import TaskAgent, TaskState


def test_shutdown_waits_for_explicit_approval():
    agent = TaskAgent()
    calls = []
    result = agent.submit("bilgisayarı kapat", lambda plan: calls.append(plan.action) or "ok")
    assert not result.success
    assert result.plan.state == TaskState.WAITING_APPROVAL
    assert calls == []

    approved = agent.approve(lambda plan: calls.append(plan.action) or "ok")
    assert approved.success
    assert calls == ["system_shutdown"]


def test_application_open_also_requires_confirmation():
    agent = TaskAgent()
    result = agent.submit("chrome aç", lambda plan: "opened")
    assert result.plan.action == "application_open"
    assert result.plan.state == TaskState.WAITING_APPROVAL


def test_possessive_shutdown_request_also_needs_confirmation():
    agent = TaskAgent()
    result = agent.submit("bilgisayarımı kapat", lambda plan: "should not run")
    assert result.plan.action == "system_shutdown"
    assert result.plan.state == TaskState.WAITING_APPROVAL
    assert "Emin misiniz?" in result.message


def test_shell_request_never_runs_without_confirmation():
    agent = TaskAgent()
    calls = []
    result = agent.submit("powershell Get-ChildItem", lambda plan: calls.append(plan.action) or "ok")
    assert result.plan.action == "shell_command"
    assert result.plan.state == TaskState.WAITING_APPROVAL
    assert calls == []


def test_folder_open_requires_confirmation():
    agent = TaskAgent()
    result = agent.submit("klasör aç Belgeler", lambda plan: "opened")
    assert result.plan.action == "folder_open"
    assert result.plan.state == TaskState.WAITING_APPROVAL


def test_agent_does_not_claim_success_for_an_unverified_executor_result():
    agent = TaskAgent()

    result = agent.submit("bilgi ver", lambda plan: None)

    assert result.success is False
    assert result.plan.state == TaskState.FAILED
    assert "doğrulanamadı" in result.message


def test_file_deletion_or_move_is_high_risk_and_needs_confirmation():
    delete_result = TaskAgent().submit("dosyayı sil notlar.txt", lambda plan: "çalışmamalı")
    move_result = TaskAgent().submit("dosya taşı notlar.txt", lambda plan: "çalışmamalı")

    assert delete_result.plan.action == "file_delete"
    assert delete_result.plan.state == TaskState.WAITING_APPROVAL
    assert move_result.plan.action == "file_move"
    assert move_result.plan.state == TaskState.WAITING_APPROVAL


def test_agent_turns_unexpected_tool_errors_into_a_failed_result():
    def broken_executor(_plan):
        raise KeyError("beklenmeyen araç cevabı")

    result = TaskAgent().submit("bilgi ver", broken_executor)

    assert result.success is False
    assert result.plan.state == TaskState.FAILED
    assert "KeyError" in result.message
