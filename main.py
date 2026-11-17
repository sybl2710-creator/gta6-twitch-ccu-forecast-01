#!/usr/bin/env python3
import json
import math
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

# Put file's own directory first on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def round_half_up(val):
    d = Decimal(str(val))
    return float(d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

def compute_growth(history_hourly, day_start_dt):
    w1_start = day_start_dt - timedelta(hours=24)
    w2_start = day_start_dt - timedelta(hours=48)

    v1 = []
    v2 = []
    for row in history_hourly:
        from_str = row.get('from')
        if not from_str:
            continue
        try:
            dt = datetime.fromisoformat(from_str.replace('Z', '+00:00'))
        except:
            continue
        viewers = row.get('viewers', 0)
        if viewers is None or viewers <= 0:
            continue
        if w1_start <= dt < day_start_dt:
            v1.append(viewers)
        elif w2_start <= dt < w1_start:
            v2.append(viewers)

    if len(v1) < 6 or len(v2) < 6:
        return 1.0
    mean1 = sum(v1) / len(v1)
    mean2 = sum(v2) / len(v2)
    if mean2 <= 0:
        return 1.0
    return mean1 / mean2

def ols_fit(X, y):
    n = len(X)
    k = len(X[0])
    XtX = [[0.0] * k for _ in range(k)]
    Xty = [0.0] * k
    for i in range(n):
        xi = X[i]
        yi = y[i]
        for r in range(k):
            Xty[r] += xi[r] * yi
            for c in range(k):
                XtX[r][c] += xi[r] * xi[c]

    for r in range(k):
        XtX[r][r] += 1e-9

    M = [row[:] + [Xty[i]] for i, row in enumerate(XtX)]
    for i in range(k):
        max_row = i
        max_val = abs(M[i][i])
        for r in range(i + 1, k):
            if abs(M[r][i]) > max_val:
                max_val = abs(M[r][i])
                max_row = r
        if max_row != i:
            M[i], M[max_row] = M[max_row], M[i]

        if abs(M[i][i]) < 1e-14:
            M[i][i] += 1e-6

        for r in range(i + 1, k):
            factor = M[r][i] / M[i][i]
            for c in range(i, k + 1):
                M[r][c] -= factor * M[i][c]

    beta = [0.0] * k
    for i in range(k - 1, -1, -1):
        s = M[i][k]
        for c in range(i + 1, k):
            s -= M[i][c] * beta[c]
        beta[i] = s / M[i][i]

    return beta

def process_case(input_path, output_path):
    data = json.loads(input_path.read_text())

    history_hourly = data.get('history_hourly', [])
    known = data.get('known', [])
    p1 = 1
    known_h1 = next((row.get('viewers') for row in known if row.get('hour') == 1 or row.get('hour') == '1'), None)
    if known_h1 is not None and known_h1 > 0:
        p1 = max(1, known_h1)
    else:
        if history_hourly:
            last_v = history_hourly[-1].get('viewers')
            if last_v is not None and last_v > 0:
                p1 = max(1, last_v)

    day_start_str = data.get('day_start')
    has_valid_day_start = False
    if day_start_str:
        try:
            target_day_start = datetime.fromisoformat(day_start_str.replace('Z', '+00:00'))
            has_valid_day_start = True
        except:
            pass

    z = [-1.645, -0.674, 0.0, 0.674, 1.645]

    if not has_valid_day_start:
        hours_output = []
        for h in range(2, 25):
            sd_h = 0.15 * math.sqrt(h - 1)
            mh = float(p1)
            q_list = []
            prev_q = 0.0
            for z_val in z:
                q_val = mh * math.exp(z_val * sd_h)
                q_val = max(0.01, min(1e9, q_val))
                if q_val < prev_q:
                    q_val = prev_q
                prev_q = q_val
                q_list.append(round_half_up(q_val))
            for i in range(1, len(q_list)):
                if q_list[i] < q_list[i-1]:
                    q_list[i] = q_list[i-1]
            hours_output.append({
                'hour': h,
                'q': q_list
            })
        out_obj = {'hours': hours_output}
        output_path.write_text(json.dumps(out_obj, separators=(',', ':')) + '\n', encoding='utf-8')
        return

    g_target = compute_growth(history_hourly, target_day_start)

    # Process comparables
    comparables = data.get('comparables', [])
    usable_curves = []
    for comp in comparables:
        name = comp.get('name', '')
        if 'grand theft auto vi' in name.lower():
            continue
        comp_day_start_str = comp.get('day_start')
        if not comp_day_start_str:
            continue
        try:
            c_start = datetime.fromisoformat(comp_day_start_str.replace('Z', '+00:00'))
        except:
            continue

        hourly = comp.get('hourly', [])
        hour_map = {}
        for row in hourly:
            from_str = row.get('from')
            if not from_str:
                continue
            try:
                dt = datetime.fromisoformat(from_str.replace('Z', '+00:00'))
            except:
                continue
            viewers = row.get('viewers', 0)
            if viewers is None or viewers <= 0:
                continue
            offset = int((dt - c_start).total_seconds() // 3600)
            if 0 <= offset < 24:
                h = offset + 1
                hour_map[h] = viewers

        if len(hour_map) == 24:
            cp1 = hour_map[1]
            cg = compute_growth(hourly, c_start)
            usable_curves.append({
                'p1': cp1,
                'g': cg,
                'hours': hour_map
            })

    z = [-1.645, -0.674, 0.0, 0.674, 1.645]

    hours_output = []

    if len(usable_curves) < 10:
        # Fallback to persistence baseline
        for h in range(2, 25):
            sd_h = 0.15 * math.sqrt(h - 1)
            mh = float(p1)
            q_list = []
            prev_q = 0.0
            for z_val in z:
                q_val = mh * math.exp(z_val * sd_h)
                q_val = max(0.01, min(1e9, q_val))
                if q_val < prev_q:
                    q_val = prev_q
                prev_q = q_val
                q_list.append(round_half_up(q_val))
            for i in range(1, len(q_list)):
                if q_list[i] < q_list[i-1]:
                    q_list[i] = q_list[i-1]
            hours_output.append({
                'hour': h,
                'q': q_list
            })
    else:
        lp_vals = [math.log(c['p1']) for c in usable_curves]
        min_lp = min(lp_vals)
        max_lp = max(lp_vals)

        target_lp = math.log(float(p1))
        clamped_lp = max(min_lp, min(max_lp, target_lp))
        target_log_g = math.log(max(1e-9, g_target))

        for h in range(2, 25):
            X = []
            y = []
            for c in usable_curves:
                cp1 = c['p1']
                cg = c['g']
                ch_viewers = c['hours'][h]
                lp = math.log(cp1)
                lg = math.log(max(1e-9, cg))
                X.append([1.0, lp, (lp ** 2) / 10.0, lg])
                y.append(math.log(ch_viewers / cp1))

            beta = ols_fit(X, y)

            n = len(X)
            residuals = []
            for i in range(n):
                xi = X[i]
                yi = y[i]
                pred = sum(xi[j] * beta[j] for j in range(len(xi)))
                residuals.append(yi - pred)
            var = sum(r * r for r in residuals) / n
            sd_h = max(0.15, math.sqrt(var))

            target_features = [1.0, clamped_lp, (clamped_lp ** 2) / 10.0, target_log_g]
            pred_log_ratio = sum(target_features[j] * beta[j] for j in range(len(target_features)))
            mh = float(p1) * math.exp(pred_log_ratio)

            q_list = []
            prev_q = 0.0
            for z_val in z:
                q_val = mh * math.exp(z_val * sd_h)
                q_val = max(0.01, min(1e9, q_val))
                if q_val < prev_q:
                    q_val = prev_q
                prev_q = q_val
                q_list.append(round_half_up(q_val))

            for i in range(1, len(q_list)):
                if q_list[i] < q_list[i-1]:
                    q_list[i] = q_list[i-1]

            hours_output.append({
                'hour': h,
                'q': q_list
            })

    out_obj = {
        'hours': hours_output
    }
    output_path.write_text(json.dumps(out_obj, separators=(',', ':')) + '\n', encoding='utf-8')

def main():
    input_dir = Path(os.environ.get('MAKEFUN_INPUT_DIR', '/input'))
    output_dir = Path(os.environ.get('MAKEFUN_OUTPUT_DIR', '/output'))
    output_dir.mkdir(parents=True, exist_ok=True)

    in_files = sorted(input_dir.glob('*.in'))
    for f in in_files:
        out_f = output_dir / f"{f.stem}.out"
        process_case(f, out_f)

if __name__ == '__main__':
    main()
