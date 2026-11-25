# -*- coding: utf-8 -*-
"""載入設定檔（settings.json / classification.json / rooms.json）。"""
import json
import os


def project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


class Config(object):
    def __init__(self, root=None):
        self.root = root or project_root()
        cfg_dir = os.path.join(self.root, "config")
        self.settings = load_json(os.path.join(cfg_dir, "settings.json"))
        self.classification = load_json(os.path.join(cfg_dir, "classification.json"))
        rooms_path = os.path.join(cfg_dir, "rooms.json")
        self.rooms = load_json(rooms_path) if os.path.exists(rooms_path) else {"rooms": []}
        self.out_dir = os.path.join(self.root, "outputs")
        if not os.path.isdir(self.out_dir):
            os.makedirs(self.out_dir)

    @property
    def thresholds(self):
        return self.settings.get("thresholds", {})

    @property
    def school_name(self):
        return (self.settings.get("school_name") or "").strip()

    def threshold(self, key, default):
        return self.thresholds.get(key, default)
