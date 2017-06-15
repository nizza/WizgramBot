import os
import yaml

msg_path = os.path.join(
    os.path.dirname(__file__),
    '../config/msg.yml'
)


def load_msgs():

    with open(msg_path, 'r') as f:
        _msg = yaml.load(f)
    msgs = {}
    for msg_type, langs in _msg.items():
        for lang, msg in langs.items():
            msgs.setdefault(lang, {})
            msgs[lang][msg_type] = msg

    return msgs


MESSAGES = load_msgs()
