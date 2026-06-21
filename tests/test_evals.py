from forgeflow.evals.runner import run_eval_file


def test_support_triage_eval_all_pass(examples_dir):
    suite = run_eval_file(examples_dir / "evals" / "support_triage_eval.yaml", mock=True)
    assert suite.all_passed, [
        (c.name, [(a.path, a.actual) for a in c.assertions if not a.passed]) for c in suite.cases
    ]


def test_sales_lead_eval_all_pass(examples_dir):
    suite = run_eval_file(examples_dir / "evals" / "sales_lead_qualifier_eval.yaml", mock=True)
    assert suite.all_passed, [
        (c.name, [(a.path, a.actual) for a in c.assertions if not a.passed]) for c in suite.cases
    ]


def test_eval_reports_counts(examples_dir):
    suite = run_eval_file(examples_dir / "evals" / "support_triage_eval.yaml", mock=True)
    assert suite.total == 3
    assert suite.passed == 3
