import json
import time

EPSILON = 1e-9
BENCHMARK_RUNS = 10


def normalize_label(raw_label: str) -> str:
    """라벨을 표준 라벨('Cross', 'X')로 정규화한다."""
    if not isinstance(raw_label, str):
        return "UNKNOWN"
    key = raw_label.strip().lower()
    if key in ("+", "cross"):
        return "Cross"
    if key == "x":
        return "X"
    return "UNKNOWN"


def is_valid_square_matrix(matrix, expected_size: int) -> bool:
    """2차원 배열이 expected_size x expected_size 크기의 숫자 행렬인지 검증한다."""
    if not isinstance(matrix, list) or len(matrix) != expected_size:
        return False
    for row in matrix:
        if not isinstance(row, list) or len(row) != expected_size:
            return False
        for val in row:
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                return False
    return True


def mac_operation(pattern: list, filter_matrix: list) -> float:
    """외부 라이브러리 없이 반복문으로 2차원 MAC(Multiply-Accumulate) 연산을 수행한다."""
    n = len(pattern)
    total = 0.0
    for i in range(n):
        for j in range(n):
            total += pattern[i][j] * filter_matrix[i][j]
    return total


def measure_mac_time_ms(pattern: list, filter_matrix: list, runs: int = BENCHMARK_RUNS) -> float:
    """MAC 연산 함수 호출 구간만 반복 측정하여 평균 시간(ms)을 반환한다."""
    start = time.perf_counter()
    for _ in range(runs):
        mac_operation(pattern, filter_matrix)
    end = time.perf_counter()
    return ((end - start) / runs) * 1000.0


def judge_scores(score_a: float, score_b: float, label_a: str, label_b: str) -> str:
    """허용오차(epsilon) 정책을 적용해 두 점수를 비교하고 판정 결과를 반환한다."""
    if abs(score_a - score_b) < EPSILON:
        return "UNDECIDED"
    return label_a if score_a > score_b else label_b


def input_matrix_3x3(name: str) -> list:
    """사용자로부터 3x3 행렬을 한 줄씩(공백 구분) 입력받고 검증한다."""
    print(f"{name} (3줄 입력, 공백 구분)")
    matrix = []
    while len(matrix) < 3:
        line = input(f"  {len(matrix) + 1}행: ").strip()
        parts = line.split()
        if len(parts) != 3:
            print("입력 형식 오류: 각 줄에 3개의 숫자를 공백으로 구분해 입력하세요.")
            continue
        try:
            row = [float(x) for x in parts]
        except ValueError:
            print("입력 형식 오류: 숫자만 공백으로 구분해 입력하세요.")
            continue
        matrix.append(row)
    return matrix


def run_mode_1():
    """모드 1: 사용자 입력 (3x3)"""
    print("\n#---------------------------------------")
    print("# [1] 필터 입력")
    print("#---------------------------------------")
    filter_a = input_matrix_3x3("필터 A")
    print("✓ 필터 A 저장 완료\n")
    filter_b = input_matrix_3x3("필터 B")
    print("✓ 필터 B 저장 완료")

    print("\n#---------------------------------------")
    print("# [2] 패턴 입력")
    print("#---------------------------------------")
    pattern = input_matrix_3x3("패턴")

    score_a = mac_operation(pattern, filter_a)
    score_b = mac_operation(pattern, filter_b)
    avg_time_ms = measure_mac_time_ms(pattern, filter_a, BENCHMARK_RUNS)
    result = judge_scores(score_a, score_b, "A", "B")

    print("\n#---------------------------------------")
    print("# [3] MAC 결과")
    print("#---------------------------------------")
    print(f"A 점수: {score_a:.16f}" if result == "UNDECIDED" else f"A 점수: {score_a}")
    print(f"B 점수: {score_b:.16f}" if result == "UNDECIDED" else f"B 점수: {score_b}")
    print(f"연산 시간(평균/{BENCHMARK_RUNS}회): {avg_time_ms:.4f} ms")
    if result == "UNDECIDED":
        print(f"판정: 판정 불가 (|A-B| < {EPSILON})")
    else:
        print(f"판정: {result}")

    print("\n#---------------------------------------")
    print(f"# [4] 성능 분석 (평균/{BENCHMARK_RUNS}회)")
    print("#---------------------------------------")
    print(f"{'크기':<10} {'평균 시간(ms)':<15} {'연산 횟수':<10}")
    print("-" * 37)
    print(f"{'3x3':<10} {avg_time_ms:<15.4f} {9:<10}")


def run_mode_2(json_path: str = "data.json"):
    """모드 2: data.json 분석"""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"오류: '{json_path}' 파일을 찾을 수 없습니다.")
        return
    except json.JSONDecodeError as e:
        print(f"오류: '{json_path}' JSON 파싱 실패 ({e})")
        return

    raw_filters = data.get("filters", {})
    raw_patterns = data.get("patterns", {})

    print("\n#---------------------------------------")
    print("# [1] 필터 로드")
    print("#---------------------------------------")
    filters = {}
    for size_key, filter_dict in raw_filters.items():
        normalized_group = {}
        for f_name, f_matrix in filter_dict.items():
            std_name = normalize_label(f_name)
            normalized_group[std_name] = f_matrix
        filters[size_key] = normalized_group
        loaded_labels = ", ".join(normalized_group.keys())
        print(f"✓ {size_key:<7} 필터 로드 완료 ({loaded_labels})")

    print("\n#---------------------------------------")
    print("# [2] 패턴 분석 (라벨 정규화 적용)")
    print("#---------------------------------------")
    total_count = 0
    pass_count = 0
    fail_cases = []
    benchmark_samples = {}

    for pattern_key, item in raw_patterns.items():
        total_count += 1
        print(f"--- {pattern_key} ---")

        parts = pattern_key.split("_")
        if len(parts) < 3 or parts[0] != "size" or not parts[1].isdigit():
            reason = "패턴 키 형식 오류 (size_{N}_{idx} 형식이 아님)"
            print(f"판정: ERROR | FAIL ({reason})")
            fail_cases.append((pattern_key, reason))
            continue

        n = int(parts[1])
        size_key = f"size_{n}"

        if size_key not in filters or "Cross" not in filters[size_key] or "X" not in filters[size_key]:
            reason = f"'{size_key}'에 해당하는 Cross/X 필터 없음"
            print(f"판정: ERROR | FAIL ({reason})")
            fail_cases.append((pattern_key, reason))
            continue

        cross_filter = filters[size_key]["Cross"]
        x_filter = filters[size_key]["X"]
        pattern_matrix = item.get("input")
        expected_label = normalize_label(item.get("expected"))

        if not (
            is_valid_square_matrix(pattern_matrix, n)
            and is_valid_square_matrix(cross_filter, n)
            and is_valid_square_matrix(x_filter, n)
        ):
            reason = f"크기 불일치 또는 잘못된 행렬 데이터 (기대 크기: {n}x{n})"
            print(f"판정: ERROR | FAIL ({reason})")
            fail_cases.append((pattern_key, reason))
            continue

        if n not in benchmark_samples:
            benchmark_samples[n] = (pattern_matrix, cross_filter)

        cross_score = mac_operation(pattern_matrix, cross_filter)
        x_score = mac_operation(pattern_matrix, x_filter)
        decision = judge_scores(cross_score, x_score, "Cross", "X")

        if decision == "UNDECIDED":
            print(f"Cross 점수: {cross_score:.16f}")
            print(f"X 점수:     {x_score:.16f}")
            reason = f"동점(UNDECIDED) 처리 규칙 적용 (|Cross-X| < {EPSILON})"
            print(f"판정: {decision} | expected: {expected_label} | FAIL (동점 규칙)")
            fail_cases.append((pattern_key, reason))
        elif decision == expected_label:
            print(f"Cross 점수: {cross_score:.4f}")
            print(f"X 점수:     {x_score:.4f}")
            print(f"판정: {decision} | expected: {expected_label} | PASS")
            pass_count += 1
        else:
            print(f"Cross 점수: {cross_score:.4f}")
            print(f"X 점수:     {x_score:.4f}")
            reason = f"예상값 불일치 (판정: {decision}, expected: {expected_label})"
            print(f"판정: {decision} | expected: {expected_label} | FAIL")
            fail_cases.append((pattern_key, reason))

    sample_3x3 = [
        [0.0, 1.0, 0.0],
        [1.0, 1.0, 1.0],
        [0.0, 1.0, 0.0],
    ]
    benchmark_samples[3] = (sample_3x3, sample_3x3)

    print("\n#---------------------------------------")
    print(f"# [3] 성능 분석 (평균/{BENCHMARK_RUNS}회)")
    print("#---------------------------------------")
    print(f"{'크기':<10} {'평균 시간(ms)':<15} {'연산 횟수(N^2)':<12}")
    print("-" * 40)
    for size in sorted(benchmark_samples.keys()):
        pat, flt = benchmark_samples[size]
        avg_ms = measure_mac_time_ms(pat, flt, BENCHMARK_RUNS)
        print(f"{f'{size}x{size}':<10} {avg_ms:<15.4f} {size * size:<12}")

    print("\n#---------------------------------------")
    print("# [4] 결과 요약")
    print("#---------------------------------------")
    print(f"총 테스트: {total_count}개")
    print(f"통과: {pass_count}개")
    print(f"실패: {len(fail_cases)}개")

    if fail_cases:
        print("\n실패 케이스:")
        for case_id, reason in fail_cases:
            print(f"- {case_id}: {reason}")


def main():
    while True:
        print("\n=== Mini NPU Simulator ===")
        print("[모드 선택]")
        print("1. 사용자 입력 (3x3)")
        print("2. data.json 분석")
        print("0. 종료")
        choice = input("선택: ").strip()

        if choice == "1":
            run_mode_1()
        elif choice == "2":
            run_mode_2("data.json")
        elif choice == "0":
            print("프로그램을 종료합니다.")
            break
        else:
            print("잘못된 입력입니다. 1, 2, 0 중 하나를 입력하세요.")


if __name__ == "__main__":
    main()