# -*- coding: utf-8 -*-
import csv, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')

def norm(s):
    s = s or ''
    out = []
    for ch in s:
        o = ord(ch)
        if 0xFF01 <= o <= 0xFF5E:
            out.append(chr(o - 0xFEE0))
        elif o == 0x3000:
            out.append('')
        else:
            out.append(ch)
    s = ''.join(out).lower()
    s = re.sub(r'(二次)?公告|正式徵件|申請須知|主題式研發計畫|補助計畫|輔導申請須知', '', s)
    s = re.sub(r'1\d{2}\s*[-~至]\s*1\d{2}\s*年度?|1\d{2}\s*年度?|民國', '', s)
    s = re.sub(r'[(（]\s*\d+\s*[)）]', '', s)
    s = re.sub(r'經濟部產業發展署|經濟部|財團法人中衛發展中心輔導', '', s)
    s = re.sub(r'[\s\-－—~、,，_｜|。：:「」『』（）()【】\'\"／/+’]', '', s)
    return s

def bg(s):
    if len(s) < 2:
        return set([s]) if s else set()
    return set(s[i:i+2] for i in range(len(s) - 1))

def jac(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

CITIES = ['桃園', '宜蘭', '高雄', '南投', '苗栗', '新竹', '彰化', '雲林', '嘉義',
          '基隆', '臺中', '台中', '屏東', '臺東', '台東', '花蓮', '金門', '連江', '澎湖']

# 讀 master
mrows = list(csv.DictReader(open(os.path.join(DATA, '時程金額萃取結果.csv'), encoding='utf-8-sig')))
master = []
for r in mrows:
    for f in ('計畫名稱', '原始檔名'):
        nm = r.get(f) or ''
        n = norm(nm)
        if len(n) >= 5 and not n.startswith('aoc'):   # 過濾過短/通用/佔位名
            master.append((bg(n), nm, r['部門']))

def city_sbir_in_master(city):
    for r in mrows:
        blob = (r.get('計畫名稱', '') + r.get('原始檔名', '') + r.get('部門', ''))
        if city in blob and re.search(r'SBIR|sbir|地方產業創新研發|地方型', blob):
            return r['部門'] + '|' + (r.get('計畫名稱') or r.get('原始檔名'))
    return None

rows = list(csv.DictReader(open(os.path.join(DATA, 'compare_list.csv'), encoding='utf-8-sig')))
out = []
for r in rows:
    name = r['計畫名稱']
    u = norm(name)
    ub = bg(u)
    is_sbir = bool(re.search(r'SBIR|sbir|地方型|地方產業創新研發', name))
    matched_city = None
    if is_sbir:
        for c in CITIES:
            if c in name:
                hit = city_sbir_in_master(c)
                if hit:
                    matched_city = (c, hit)
                break
    if matched_city:
        status, sim, near, dep = '命中(在master)', 1.0, matched_city[1].split('|')[1], matched_city[1].split('|')[0]
    else:
        best = (0.0, '', '')
        for mb, mname, mdep in master:
            s = jac(ub, mb)
            if s > best[0]:
                best = (s, mname, mdep)
        sim = round(best[0], 2)
        near, dep = best[1], best[2]
        if sim >= 0.5:
            status = '命中(在master)'
        elif sim >= 0.3:
            status = '疑似待確認'
        else:
            status = '不在master'
        if is_sbir and not matched_city:
            status = '疑似待確認' if status == '命中(在master)' else status
    out.append({'序號': r['序號'], '計畫名稱': name, '機關': r['機關'],
                '狀態': status, '相似度': sim, '最相近master計畫': near, 'master部門': dep})

cols = ['序號', '計畫名稱', '機關', '狀態', '相似度', '最相近master計畫', 'master部門']
with open(os.path.join(DATA, 'compare_result.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for r in out:
        w.writerow(r)
from collections import Counter
print('total', len(out), dict(Counter(r['狀態'] for r in out)))
