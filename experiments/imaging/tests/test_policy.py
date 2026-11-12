from gateway import permitted_path
from synthetic import STUDY_UID, SERIES_UID, instance_uid


def test_only_assigned_hierarchy_is_allowed():
    root = f'studies/{STUDY_UID}'
    assert permitted_path(root + '/series')
    assert permitted_path(root + f'/series/{SERIES_UID}/instances/{instance_uid(1)}/frames/1')
    for path in ['studies', 'studies/9/series', root + '/series/9/instances', root + '/series/' + SERIES_UID + '/instances/9/frames/1', '../system', root + '/../../system', root + '/series/' + SERIES_UID + '/instances/' + instance_uid(1) + '/frames/999']:
        assert not permitted_path(path), path
