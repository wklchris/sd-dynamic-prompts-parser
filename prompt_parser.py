from numpy.random import default_rng
from pathlib import Path
import pyparsing as pp
from pyparsing import pyparsing_common as ppc
import re, yaml

def load_wildcard_txts(wildcard_dir, wildcard_yaml):
    """Load wildcards from txts in the wildcard directory and save them to YAML file."""
    files = Path(wildcard_dir).rglob("*.txt")
    data = []
    for txtfile in files:
        rel_fpath = Path(txtfile).relative_to(wildcard_dir)
        key = f"{rel_fpath.parent.as_posix()}/{rel_fpath.stem}".lstrip("./")
        
        with open(txtfile, 'r') as f:
            val = [line for line in f.read().splitlines() if not line.startswith('#')]
        data[key] = val

    with open(wildcard_yaml, 'w') as f:
        yaml.dump(data, f)
    print(f"Wildcards files loaded and write to {wildcard_yaml}")
    return data

def load_wildcard(wildcard_yaml='wildcards.yaml', wildcard_dir='wildcard'):
    """Load wildcard from YAML file. If not exists, load from the wildcard directory."""
    try:
        if Path(wildcard_yaml).is_file():
            error_msg = f"YAML file: {wildcard_yaml}"
            with open(wildcard_yaml, 'r') as f:
                data = yaml.safe_load(f)
        else:
            error_msg = f"folder: {wildcard_dir}"
            data = load_wildcard_txts()
    except Exception as e:
        print(f"Fail to load wildcard from {error_msg}")
    return data

def init_parser():
    """
    BNF for the prompt syntax:
    
    expr        :=  item*
    item        :=  random | wildcard | text
    random      :=  '{' [ random_pre ] random_item ( '|' random_item )* '}'
    random_pre  :=  draw_nums '$$' [ draw_sep '$$' ]
    draw_nums   :=  integers [ '-' integers ]
    draw_sep    :=  ( alphas | nums | ',' | ' ' )+
    random_item :=  [ weight '::' ] expr
    weight      :=  nums
    wildcard    :=  '__' text '__'
    text        :=  ( alphas | nums | ',_()\/-' )+
    """
    LBRACK, RBRACK, HYPHEN, VERT, DCOLON, DDOLLAR, DULINE = map(pp.Suppress, '{ } - | :: $$ __'.split())
    integers = pp.Word(pp.nums)
    nums = pp.Word(pp.nums + '.')
    
    expr = pp.Forward()
    draw_lower = integers.set_parse_action(ppc.convert_to_integer)
    draw_upper = integers.set_parse_action(ppc.convert_to_integer)
    draw_nums = (draw_lower + pp.Optional(HYPHEN + draw_upper))
    draw_sep = pp.Word(pp.alphanums + ',' + ' ', exclude_chars='$')
    random_pre = draw_nums + DDOLLAR + pp.Optional(draw_sep + DDOLLAR)
    weight = nums.set_parse_action(ppc.convert_to_float)
    random_item = pp.Group(pp.Optional(weight + DCOLON) + expr)
    random = pp.Group(LBRACK +
                      pp.Optional(random_pre) +
                      pp.DelimitedList(random_item, delim=VERT) +
                      RBRACK)
    text = pp.Word(pp.alphanums + ',_()\/-' + ' ').leave_whitespace()
    wildcard = (DULINE + text + DULINE)
    item = (random | wildcard | text)
    expr <<= pp.ZeroOrMore(item)
    return expr

def parse_line(line, parser):
    result = parser.parse_string(line).as_list()
    return result

def draw_wildcard(line: str, wildcards: dict, rng):
    regex = r'__[\w\,\_\(\)\/\-]+__'
    repl_func = lambda m: rng.choice(wildcards.get(m.group().strip('_'), [m.group()]))
    prev, replaced = line, ''
    while True:
        replaced = re.sub(regex, repl_func, prev)
        if replaced == prev:
            break
        prev = replaced
    return replaced

def draw_random(parsed: list, rng):
    # Parsed List Strutcture: 
    #   lower, upper, sep, *choices
    #   lower, upper, *choices
    #   lower, sep, *choices
    #   lower, *choices
    #   *choices
    lower, upper, sep = 1, 1, ', '
    for i, x in enumerate(parsed):
        if i == 0:
            if isinstance(x, int):
                lower = x
            else:
                choices = parsed[i:]
                break
        elif i == 1:
            if isinstance(x, int):
                upper = x
            elif isinstance(x, str):
                sep = x
            else:
                choices = parsed[i:]
                break
        elif i == 2:
            if isinstance(x, str):
                sep = x
            else:
                choices = parsed[i:]
                break
        else:
            choices = parsed[i:]
            break
    # Choices Element Strucutre
    #   [choice]
    #   [weight, choice]
    n = len(choices)
    weights = [1.0 for _ in range(n)]
    items = ['' for _ in range(n)]
    for i, c in enumerate(choices):
        if any(isinstance(x, list) for x in c):  # nested random
            items[i] = draw_random(c, rng)
        elif isinstance(c, str):  # Plain text may occur
            items[i] = c
        elif len(c) > 1:
            weights[i] = c[0]
            items[i] = c[1]
        else:
            items[i] = c[0] if c else ''  # Random item can be empty
    
    weights = [w/sum(weights) for w in weights]
    lower = min(max(lower, 1), n)
    upper = min(max(upper, lower), n)
    draw_num = rng.choice(range(lower, upper+1))
    selected = rng.choice(items, size=draw_num, p=weights, replace=False).tolist()
    s = sep.join(selected)
    return s

def process_parsed_result(parsed: list, wildcards: dict, rng, parser):
    """Return a prompt string after processing wildcards/randoms in the parsed result list."""
    lst = []
    for parsed_item in parsed:
        lower, upper, sep = 1, 1, ', '
        match parsed_item:
            case list(random_lst):
                replaced = draw_random(random_lst, rng)
                lst.append(replaced)
            case str(wildcard_str):
                _replaced = draw_wildcard(wildcard_str, wildcards, rng)
                _random_lst = parser.parse_string(_replaced).as_list()
                replaced = draw_random(_random_lst, rng)
                lst.append(replaced)
            case _:
                lst.append(('Others', parsed_item))
    s = ''.join(lst)
    return s

def parse_prompt(prompt: str, wildcards: dict, seed=-1, rng=None, parser=None):
    expr = init_parser() if not parser else parser
    if not rng:
        rng = default_rng(seed) if seed >= 0 else default_rng()
    # Draw wildcard before parse
    line = draw_wildcard(prompt, wildcards, rng)
    parsed = expr.parse_string(line).as_list()
    result = process_parsed_result(parsed, wildcards, rng=rng, parser=expr)
    return result

if __name__ == "__main__":
    prompt = 'masterpiece, best quality, 1girl, character_name \(artwork_name\), __color__ hair, {long|short|medium} hair, {1-3$$, $$long dress|__cloth/dress-style__|__color__ dress}, looking {back|to the side|up|down|to the viewer}, (cowboy shot), from {2::behind|side|below|above}, {outdoors|indoors|__scene__}, professional lighting'
    wildcards = load_wildcard()
    for i in range(3):
        result = parse_prompt(prompt, wildcards)
        print(i, result, sep='\n', end='\n\n')
