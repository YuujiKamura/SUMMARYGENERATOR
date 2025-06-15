# flake8: noqa

import os

from src.utils.thermometer_utils import process_thermometer_records
# services.log_utils はルート/logs へ出力
from src.services.log_utils import step_log

def match_image_to_records(
    image_json_dict,
    records,
    mapping=None,
):
    """
    画像パス→キャッシュJSON（img_json）→ChainRecordリストのdictを返す
    image_json_dict: {image_path: img_json, ...}
    mapping: role_mapping（Noneの場合は空dictで渡す）
    """
    from src.utils.record_matching_utils import match_roles_records_one_stop
    result = {}
    if mapping is None:
        mapping = {}
    for img_path, img_json in image_json_dict.items():
        matched = match_roles_records_one_stop(
            img_json,
            mapping,
            records,
        )
        result[img_path] = matched
    return result

# ---------------------------------------------------------------------------
# ImageMatchingService: 画像エントリのマッチング、温度計サイクルマッチングを担当
# ---------------------------------------------------------------------------
class ImageMatchingService:
    """
    画像⇄レコードマッチング用サービス。

    DB には直接依存せず、画像一覧取得関数と bbox 取得関数を DI で受け取る。
    get_images_func: () -> List[Dict]  ※各 dict に少なくとも image_path, id を含む
    get_bboxes_func: (image_id: int) -> List[Dict]  ※各 dict に role を含む
    """

    def __init__(self, *, get_images_func=None, get_bboxes_func=None):
        self.get_images_func = get_images_func
        self.get_bboxes_func = get_bboxes_func

    def match_image_to_records(
        self,
        entries,
        role_mapping,
        remarks_to_chain_record,
        debug_callback=None,
    ):
        image_json_dict: dict[str, dict] = {}
        for e in entries:
            path = getattr(e, 'path', None) or getattr(e, 'image_path', None)
            roles = getattr(e, 'roles', None)
            if not roles or not isinstance(roles, list):
                roles = []
                if (
                    hasattr(e, 'cache_json')
                    and e.cache_json
                    and 'bboxes' in e.cache_json
                ):
                    for b in e.cache_json['bboxes']:
                        if 'role' in b and b['role']:
                            roles.append(b['role'])
                # --- fallback: DI された DB アクセスで role を取得 ---
                if (
                    not roles
                    and path
                    and self.get_images_func
                    and self.get_bboxes_func
                ):
                    try:
                        img_rows = [
                            row
                            for row in self.get_images_func()
                            if row.get('image_path') == path
                        ]
                        if img_rows:
                            image_id = img_rows[0].get('id')
                            if image_id is not None:
                                bbox_rows = self.get_bboxes_func(image_id)
                                for b in bbox_rows:
                                    role = b.get('role')
                                    if role:
                                        roles.append(role)
                    except Exception:
                        # 例外が出てもロールが取れなければ空のまま続行
                        pass
            if debug_callback:
                debug_callback(
                    path,
                    f"[get_match_results] roles: {roles}",
                )
            img_json = {
                'image_path': path,
                'roles': roles
            }
            if hasattr(e, 'cache_json') and e.cache_json:
                img_json.update({
                    'img_w': e.cache_json.get('img_w'),
                    'img_h': e.cache_json.get('img_h'),
                    'bboxes': e.cache_json.get('bboxes', [])
                })
            image_json_dict[path] = img_json
        step_log('image_json_dict', image_json_dict)
        # DBからChainRecordを取得
        # ローカルでChainRecord変換する場合:
        #   records = [
        #       ChainRecord.from_dict(r)
        #       for r in remarks_to_chain_record.values()
        #   ]
        records = list(remarks_to_chain_record.values())
        step_log('chain_records_match', [r.__dict__ for r in records])
        match_results = match_image_to_records(
            image_json_dict,
            records,
            role_mapping,
        )
        # --- ファイル名→マッチしたレコード（dict形式）のログを生成 ---
        detailed_log = {}
        for img_path, recs in match_results.items():
            fname = os.path.basename(img_path)
            records_list = []
            # match_results は ImageEntry か list を返す想定
            chain_recs = None
            if isinstance(recs, list):
                chain_recs = recs
            elif hasattr(recs, 'chain_records'):
                chain_recs = recs.chain_records
            if chain_recs:
                for r in chain_recs:
                    # ChainRecord なら to_dict で、dict ならそのまま、その他は __dict__
                    if hasattr(r, 'to_dict'):
                        records_list.append(r.to_dict())
                    elif isinstance(r, dict):
                        records_list.append(r)
                    elif hasattr(r, '__dict__'):
                        records_list.append(dict(r.__dict__))
                    else:
                        records_list.append(str(r))
            detailed_log[fname] = records_list

        step_log('S3_match_results', detailed_log)
        return match_results

    def process_thermometer_records(self, candidates_list, debug_entries=None):
        return process_thermometer_records(
            candidates_list,
            debug_entries=debug_entries,
        )
