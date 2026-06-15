from slurm_job_doctor.parsers.sbatch_parser import parse_sbatch_text

EXAMPLE = """#!/bin/bash
#SBATCH --job-name=train_model
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=logs/%j.out
#SBATCH --error=logs/%j.err

module load cuda
source activate ml
python train.py
"""


def test_parses_long_directives():
    script = parse_sbatch_text(EXAMPLE, path="train.sbatch")
    assert script.job_name == "train_model"
    assert script.partition == "gpu"
    assert script.gres == "gpu:1"
    assert script.cpus_per_task == "16"
    assert script.mem == "32G"
    assert script.time == "02:00:00"
    assert script.output == "logs/%j.out"
    assert script.error == "logs/%j.err"
    assert script.gpu_count == 1


def test_preserves_layout_and_body():
    script = parse_sbatch_text(EXAMPLE)
    assert script.shebang == "#!/bin/bash"
    assert script.lines[0] == "#!/bin/bash"
    # blank line between directives and commands is preserved verbatim
    assert "" in script.lines
    assert script.body == ["module load cuda", "source activate ml", "python train.py"]
    assert len(script.directives) == 8


def test_directive_line_indices_point_at_source():
    script = parse_sbatch_text(EXAMPLE)
    mem = next(d for d in script.directives if d.key == "mem")
    assert script.lines[mem.line_index] == "#SBATCH --mem=32G"
    assert mem.raw == "#SBATCH --mem=32G"


def test_short_options_map_to_long():
    text = "#!/bin/bash\n#SBATCH -p compute\n#SBATCH -c 8\n#SBATCH -N2\n#SBATCH -t 01:00:00\n"
    script = parse_sbatch_text(text)
    assert script.partition == "compute"
    assert script.cpus_per_task == "8"
    assert script.nodes == "2"
    assert script.time == "01:00:00"


def test_space_separated_and_flag_directives():
    text = "#SBATCH --mem 16G\n#SBATCH --exclusive\n#SBATCH --mem-per-cpu=4G\n"
    script = parse_sbatch_text(text)
    assert script.mem == "16G"
    assert script.mem_per_cpu == "4G"
    flag = next(d for d in script.directives if d.key == "exclusive")
    assert flag.value is None


def test_inline_comment_is_ignored():
    script = parse_sbatch_text("#SBATCH --mem=8G  # bump this later\n")
    assert script.mem == "8G"


def test_gpu_count_from_gres_and_gpus():
    assert parse_sbatch_text("#SBATCH --gres=gpu:a100:4\n").gpu_count == 4
    assert parse_sbatch_text("#SBATCH --gres=gpu\n").gpu_count == 1
    assert parse_sbatch_text("#SBATCH --gpus=2\n").gpu_count == 2
    assert parse_sbatch_text("#SBATCH --mem=8G\n").gpu_count is None


def test_last_directive_wins():
    script = parse_sbatch_text("#SBATCH --mem=8G\n#SBATCH --mem=16G\n")
    assert script.mem == "16G"
