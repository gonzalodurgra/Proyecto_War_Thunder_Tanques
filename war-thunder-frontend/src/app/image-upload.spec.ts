import { TestBed } from '@angular/core/testing';

import { ImageUpload } from './image-upload';

describe('ImageUpload', () => {
  let service: ImageUpload;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ImageUpload);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
