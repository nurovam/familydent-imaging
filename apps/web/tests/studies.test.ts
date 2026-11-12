import { test } from 'node:test';
import assert from 'node:assert/strict';
import { filterStudies, studies } from '../src/studies.ts';
test('search combines identifier, modality and status without changing fixtures', () => {
  assert.equal(filterStudies(studies, ' fd-demo-001 ', 'CBCT', 'new').length, 1);
  assert.equal(filterStudies(studies, 'FD-DEMO-001', 'OPG', 'all').length, 0);
  assert.equal(filterStudies(studies, '', 'all', 'viewed').length, 1);
  assert.equal(filterStudies(studies, 'отсутствует', 'all', 'all').length, 0);
  assert.equal(studies.length, 3);
});
