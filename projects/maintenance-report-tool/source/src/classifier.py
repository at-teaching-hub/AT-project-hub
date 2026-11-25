# -*- coding: utf-8 -*-
"""維修項目分類：依分類字典（classification.json）比對。"""
from textutil import match_rule, norm


class Classifier(object):
    def __init__(self, classification):
        self.categories = classification.get("categories") or []
        self.fallback = classification.get("fallback") or []
        self.unclassified = classification.get("unclassified") or {
            "cat": "OTHER", "name": "其他／待分類", "sub": "未分類"
        }
        self.invalid = [norm(k) for k in (classification.get("invalid_keywords") or []) if norm(k)]

    def _first_pass(self, text):
        if not text:
            return None
        for category in self.categories:
            for sub in category.get("subs") or []:
                if match_rule(text, sub):
                    return {
                        "cat": category.get("id"),
                        "cat_name": category.get("name"),
                        "sub": sub.get("name"),
                    }
        return None

    def classify(self, item, detail):
        base = {
            "cat": self.unclassified.get("cat", "OTHER"),
            "cat_name": self.unclassified.get("name", "其他／待分類"),
            "sub": self.unclassified.get("sub", "未分類"),
            "matched_by": "none",
            "is_invalid": False,
        }
        norm_item = norm(item)
        if norm_item and norm_item in self.invalid:
            base["is_invalid"] = True
            return base
        hit = self._first_pass(norm_item)
        if hit:
            base.update(hit)
            base["matched_by"] = "item"
            return base
        combined = norm_item + "|" + norm(detail)
        hit = self._first_pass(combined)
        if hit:
            base.update(hit)
            base["matched_by"] = "item+detail"
            return base
        for rule in self.fallback:
            if match_rule(combined, rule):
                return {
                    "cat": rule.get("cat"),
                    "cat_name": rule.get("cat_name"),
                    "sub": rule.get("sub"),
                    "matched_by": "fallback",
                    "is_invalid": False,
                }
        return base
