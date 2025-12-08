import { TestBed } from '@angular/core/testing';

import { TanksStatsServiceTs } from './tanks-stats.service.ts';

describe('TanksStatsServiceTs', () => {
  let service: TanksStatsServiceTs;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(TanksStatsServiceTs);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
