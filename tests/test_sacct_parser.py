from slurm_job_doctor.parsers.sacct_parser import (
    expand_nodelist,
    parse_sacct_text,
)

# The README's single-row example.
SIMPLE = """JobID|JobName|State|ExitCode|Elapsed|Timelimit|ReqMem|MaxRSS|AllocCPUS|NTasks|NodeList
123456|train|OUT_OF_MEMORY|0:125|00:12:31|01:00:00|16Gn|15700M|8|1|node001
"""

# A realistic multi-row dump: MaxRSS lives on the .batch step, not the main row.
MULTIROW = """JobID|JobName|State|ExitCode|Elapsed|Timelimit|ReqMem|MaxRSS|AllocCPUS|NTasks|NNodes|NodeList|TotalCPU
123456|train|OUT_OF_MEMORY|0:125|00:12:31|01:00:00|16Gn||8||1|node001|01:30:00
123456.batch|batch|OUT_OF_MEMORY|0:125|00:12:31||16Gn|15700M|8|1|1|node001|01:29:50
123456.extern|extern|COMPLETED|0:0|00:12:31||16Gn|1200K|8|1|1|node001|00:00:00
"""


def test_simple_row_matches_readme():
    (record,) = parse_sacct_text(SIMPLE)
    assert record.job_id == "123456"
    assert record.job_name == "train"
    assert record.state == "OUT_OF_MEMORY"
    assert record.is_oom
    assert record.requested_memory_mb == 16384
    assert record.max_rss_mb == 15700
    assert record.allocated_cpus == 8
    assert record.elapsed_seconds == 751
    assert record.timelimit_seconds == 3600
    assert record.nodes == ["node001"]


def test_multirow_merges_maxrss_from_step():
    (record,) = parse_sacct_text(MULTIROW)
    assert record.job_id == "123456"
    assert record.state == "OUT_OF_MEMORY"
    # MaxRSS is taken from the batch step (15700M), not the empty main row
    assert record.max_rss_mb == 15700
    assert record.ntasks == 1
    assert record.requested_memory_mb == 16384
    assert record.total_cpu_seconds == 5400  # 01:30:00


def test_cpu_efficiency_and_memory_utilization():
    (record,) = parse_sacct_text(MULTIROW)
    # 5400 / (751 * 8) ≈ 0.899
    assert record.cpu_efficiency is not None
    assert 0.88 < record.cpu_efficiency < 0.91
    # 15700 / 16384 ≈ 0.958
    assert record.memory_utilization is not None
    assert 0.95 < record.memory_utilization < 0.97


def test_per_cpu_reqmem_scales_by_alloc_cpus():
    text = "JobID|State|ReqMem|AllocCPUS|NNodes\n900|COMPLETED|4Gc|8|1\n"
    (record,) = parse_sacct_text(text)
    assert record.requested_memory_mb == 4096 * 8


def test_csv_delimiter_and_headerless():
    csv_text = "JobID,State,ReqMem,MaxRSS,AllocCPUS\n5,TIMEOUT,8G,4096M,4\n"
    (record,) = parse_sacct_text(csv_text)
    assert record.is_timeout
    assert record.requested_memory_mb == 8192
    assert record.max_rss_mb == 4096


def test_gpu_count_from_alloctres():
    text = "JobID|State|AllocTRES\n7|COMPLETED|cpu=8,mem=32G,node=1,gres/gpu=2\n"
    (record,) = parse_sacct_text(text)
    assert record.gpu_count == 2


def test_cancelled_state_base_strips_detail():
    text = "JobID|State\n8|CANCELLED by 1001\n"
    (record,) = parse_sacct_text(text)
    assert record.state_base == "CANCELLED"
    assert record.is_failed


def test_expand_nodelist():
    assert expand_nodelist("node001") == ["node001"]
    assert expand_nodelist("node[001-003]") == ["node001", "node002", "node003"]
    assert expand_nodelist("n[01,03-04],gpu02") == ["n01", "n03", "n04", "gpu02"]
    assert expand_nodelist("None assigned") == []


def test_empty_input_returns_no_records():
    assert parse_sacct_text("") == []
    assert parse_sacct_text("JobID|State\n") == []
