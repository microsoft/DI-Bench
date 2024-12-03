APPLY_PATCH_FAIL = ">>>>> Patch Failed"
APPLY_PATCH_PASS = ">>>>> Patch Succeeded"
GIT_COMMIT_FAIL = ">>>>> Git Commit Failed"
GIT_COMMIT_PASS = ">>>>> Git Commit Succeeded"
CI_TEST_FAIL = ">>>>> CI Failed"
CI_TEST_PASS = ">>>>> CI Succeeded"

KEY_INSTANCE_ID = "instance_id"


# work space management
# + workspace root
#   + instance workspace
#   + exec_testbed
#   - eval.log
#   - exec.log
#   - result.json
#   - ...
EVAL_LOG = "evaluate.log"
EVAL_RESULT = "result.json"
## Log file names
EXEC_OUTPUT_LOG = "exec_output.log"
EXEC_TESTBED = "exec_testbed"
ORACLE_TEXT_TESTBED = "oracle_text_testbed"
PRED_TEXT_TESTBED = "pred_text_testbed"
RESULTS_DIR = "results"


# evaluation results
FAILED = dict(
    exact={"TP": 0, "TN": 0, "FP": 0, "FN": 0},
    name_only={"TP": 0, "TN": 0, "FP": 0, "FN": 0},
)
