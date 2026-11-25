"""昭和48年法律第10号の移行の検査を実行し、結果を docs/validation/ に保存する。

使い方:
  python -X utf8 docs/verify.py VALIDATOR REGISTRY HOLIDAY [VALIDATOR_COMMIT]

VALIDATOR は loj-validator の実行ファイル、REGISTRY は登録台帳の main の作業ツリー、
HOLIDAY は祝日法（19480720-law-178）の main の作業ツリー。
"""
from pathlib import Path
import hashlib, json, re, subprocess, sys

repo = Path(__file__).resolve().parents[1]
exe, registry, holiday = (Path(a).resolve() for a in sys.argv[1:4])
rev = '4w4q4aq4'
v = repo / 'versions' / rev
out = repo / 'docs/validation'
out.mkdir(exist_ok=True)
jobs = [
    ('package-L0', [v, '--level', 'L0']),
    ('package-L1', [v, '--level', 'L1']),
    ('history-L3', [repo, '--level', 'L3']),
    ('rebuild', [repo, '--check', 'rebuild']),
    ('registry', [registry, '--check', 'registry', '--registration-space', 'law-of-japan']),
    ('relations-L4', ['--registry', registry, '--repository', repo, '--repository', holiday,
                      '--level', 'L4', '--registration-space', 'law-of-japan']),
]
results = []
for name, args in jobs:
    args = [str(a) for a in args]
    r = subprocess.run([str(exe), 'check', *args, '--format', 'json'], capture_output=True)
    report = json.loads(r.stdout)
    # 保存する結果から、この環境の絶対パスを除く。
    text = json.dumps(report, ensure_ascii=False, indent=2)
    for label, p in (('<repo>', repo), ('<registry>', registry), ('<holiday>', holiday)):
        for form in (str(p), str(p).replace('\\', '/')):
            text = text.replace(json.dumps(form)[1:-1], label)
    (out / f'{name}.json').write_bytes((text + '\n').encode())
    shown = [a if not Path(a).is_absolute() else Path(a).name for a in args]
    results.append({'name': name, 'exitCode': r.returncode, 'args': shown, 'results': report.get('results')})
    print(name, r.returncode, report.get('results'))
assert all(r['exitCode'] == 0 for r in results), 'Unexpected validation result'

for d in json.loads((repo / 'docs/sources/downloads.json').read_text(encoding='utf-8')):
    assert hashlib.sha256((repo / 'docs/sources' / d['file']).read_bytes()).hexdigest() == d['sha256'], d['file']

# 旧本文（凍結点）と版の字句が、リンク・マーカー・項番号・空白を除いて一致すること。
def show(path):
    return subprocess.check_output(['git', '-C', str(repo), 'show', f'{frozen}:{path}']).decode()
frozen = '1a66a7feb0b05a548455d5c4e489dd8376daed81'
old = show('article.md').split('\n', 1)[1] + show('supplementary_provision.md').split('附　則（昭和四八年四月一二日法律第十号）', 1)[1]
new = (v / 'main.md').read_text(encoding='utf-8') + (v / 'supplement.md').read_text(encoding='utf-8')
def norm(t):
    t = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', t)
    t = re.sub(r'<!--.*?-->', '', t)
    t = t.replace('# 附　則', '')
    t = re.sub(r'^\s*[0-9１-９]+[.　]\s*', '', t, flags=re.M)
    return re.sub(r'[\s\\]', '', t)
assert norm(old) == norm(new), 'legacy wording differs'

# 旧ブランチの先端が凍結点のままであること。
refs = {'legacy/main': frozen, 'refs/remotes/origin/master': '0a62468ab79b5ade68a34e29a105082173fb8d90'}
for ref, sha in refs.items():
    assert subprocess.check_output(['git', '-C', str(repo), 'rev-parse', ref], text=True).strip() == sha, ref

def head(p):
    return subprocess.check_output(['git', '-C', str(p), 'rev-parse', 'HEAD'], text=True).strip()
summary = {
    'revision': rev,
    'checks': results,
    'sourceHashesMatch': True,
    'legacyWordingMatches': True,
    'legacyRefsUnchanged': True,
    'heads': {'loj-registry': head(registry), '19480720-law-178': head(holiday), 'loj-validator': sys.argv[4] if len(sys.argv) > 4 else None},
    'binarySha256': hashlib.sha256(exe.read_bytes()).hexdigest(),
}
(out / 'summary.json').write_bytes((json.dumps(summary, ensure_ascii=False, indent=2) + '\n').encode())
