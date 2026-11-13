"""
indic-phonetic web demo.

    pip install -e '.[demo]'
    python demo/app.py

Type a name or place as it was heard (Roman, Devanagari or Tamil), pick a
reference list, and see the closest matches and why the top one matched.
"""
import csv
from pathlib import Path

import gradio as gr

from indic_phonetic import Matcher, UnsupportedScriptError, distance, explain, to_roman

DATA = Path(__file__).resolve().parents[1] / "benchmarks" / "data"


def _read(name: str) -> list[dict]:
    with open(DATA / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


_districts = _read("districts.csv")
_state = {r["district"]: r["state"] for r in _districts}
_places = [(r["district"], r["district"]) for r in _districts] + \
          [(r["district"], r["alias"]) for r in _read("place_aliases.csv")]
_people = [(r["full_name"], r["full_name"]) for r in _read("people.csv")]

LISTS = {
    f"Indian districts ({len(_districts)}, plus old names)": Matcher(_places),
    f"Sample people ({len(_people)}, synthetic)": Matcher(_people),
}
CUSTOM = "My own list"

# An example policy for a voice agent, from the project this library came
# from. The library itself only returns distances.
ACCEPT, MARGIN, READ_BACK = 0.8, 1.0, 1.8


def _verdict(matches) -> str:
    if not matches:
        return "No match."
    name = matches[0].key
    best = matches[0].distance
    gap = matches[1].distance - best if len(matches) > 1 else float("inf")
    tied = [m.key for m in matches if m.distance == best]
    if len(tied) > 1 and best < READ_BACK:
        return f"**Ambiguous:** {', '.join(f'*{t}*' for t in tied)} are equally close ({best:g}). Ask which one."
    if best < ACCEPT and gap >= MARGIN:
        return f"**Accept** *{name}*: distance {best:g}, {gap:g} ahead of the next."
    if best < READ_BACK:
        return f"**Read back** “Did you say *{name}*?”: distance {best:g}, next is {gap:g} behind."
    return f"**Ask again.** The closest, *{name}*, is {best:g} away."


def match(heard: str, list_name: str, custom: str, top: int):
    heard = heard.strip()
    if not heard:
        return [], "", ""
    try:
        if list_name == CUSTOM:
            refs = [line.strip() for line in custom.splitlines() if line.strip()]
            if not refs:
                return [], "Add some names to your list, one per line.", ""
            matcher = Matcher(refs)
        else:
            matcher = LISTS[list_name]
        matches = matcher.best_match(heard, top=int(top))
    except UnsupportedScriptError as e:
        return [], f"⚠️ {e}", ""
    rows = []
    for i, m in enumerate(matches, 1):
        shown = m.key if m.key == m.text else f"{m.key} (said as {m.text})"
        where = _state.get(m.key, "") if list_name.startswith("Indian") else ""
        rows.append([i, shown, where, m.distance])
    roman = to_roman(heard)
    head = f"Heard as **{roman}**\n\n" if roman != heard.lower() else ""
    why = str(explain(heard, matches[0].text)) if matches else ""
    return rows, head + _verdict(matches), why


def compare(a: str, b: str):
    if not a.strip() or not b.strip():
        return "", ""
    try:
        d = distance(a, b)
        return f"## {d:g}", str(explain(a, b))
    except UnsupportedScriptError as e:
        return f"⚠️ {e}", ""


INTRO = """
# indic-phonetic

Match Indian names and places by how they **sound**, not how they're spelled, across Roman, Devanagari and Tamil.
Lower distance means closer; 0 means the same sounds. Pure Python, no dependencies.
"""

with gr.Blocks(title="indic-phonetic") as demo:
    gr.Markdown(INTRO)
    with gr.Tab("Match against a list"):
        with gr.Row():
            with gr.Column(scale=2):
                heard = gr.Textbox(label="What was heard", placeholder="Baadmer, बाड़मेर, Shri Vinod Kumar ji …")
                list_name = gr.Dropdown([*LISTS, CUSTOM], value=next(iter(LISTS)), label="Reference list")
                custom = gr.Textbox(label="Your list, one name per line", lines=6, visible=False)
                top = gr.Slider(1, 10, value=5, step=1, label="How many matches")
                go = gr.Button("Match", variant="primary")
            with gr.Column(scale=3):
                verdict = gr.Markdown()
                table = gr.Dataframe(headers=["#", "Match", "State", "Distance"], interactive=False, wrap=True)
                why = gr.Code(label="Why the top match", language=None, lines=10)
        places, people = list(LISTS)
        gr.Examples(
            [[q, places] for q in ["Baadmer", "बाड़मेर", "Lakhnau", "Bangalor", "திருச்சி", "Vizag"]] +
            [[q, people] for q in ["Rohun Varma", "रोहन वर्मा", "Shri Rohan Verma ji", "Varma Rohan", "R. Verma"]],
            inputs=[heard, list_name],
        )
        gr.Markdown(
            f"The verdict is an example policy from a voice agent (accept below {ACCEPT} when "
            f"{MARGIN} ahead of the next, read back below {READ_BACK}, otherwise ask again). "
            "The library returns distances only; tune thresholds on your own data."
        )
        list_name.change(lambda n: gr.update(visible=n == CUSTOM), list_name, custom)
        inputs = [heard, list_name, custom, top]
        go.click(match, inputs, [table, verdict, why])
        heard.submit(match, inputs, [table, verdict, why])

    with gr.Tab("Compare two names"):
        with gr.Row():
            a = gr.Textbox(label="Name A", value="Barmer")
            b = gr.Textbox(label="Name B", value="बाड़मेर")
        cmp = gr.Button("Compare", variant="primary")
        score = gr.Markdown()
        steps = gr.Code(label="Steps", language=None, lines=12)
        gr.Examples(
            [["Barmer", "बाड़मेर"], ["Mohan", "Rohan"], ["Vinod", "Binod"], ["Lakshmi", "லட்சுமி"],
             ["Venkatesh", "வெங்கடேஷ்"], ["Singh", "सिंह"], ["Shri Mohan Lal ji", "Mohan Lal"],
             ["Kumar Ramesh Singh", "Ramesh Kumar Singh"], ["Patil", "Patel"]],
            inputs=[a, b],
        )
        cmp.click(compare, [a, b], [score, steps])

if __name__ == "__main__":
    demo.launch()
