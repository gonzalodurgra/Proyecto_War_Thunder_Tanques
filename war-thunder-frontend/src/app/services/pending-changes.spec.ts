import { TestBed } from '@angular/core/testing';

import { PendingChangesService } from './pending-changes';

describe('PendingChanges', () => {
  let service: PendingChangesService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(PendingChangesService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
