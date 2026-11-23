import { TestBed } from '@angular/core/testing';

import { ImageUploadService } from './image-upload';

describe('ImaloadgeUpSerload', () => {
  let service: ImageUploadService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ImageUploadService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
