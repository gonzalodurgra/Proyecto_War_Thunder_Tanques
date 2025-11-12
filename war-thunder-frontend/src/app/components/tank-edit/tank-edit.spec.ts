import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TankEdit } from './tank-edit';

describe('TankEdit', () => {
  let component: TankEdit;
  let fixture: ComponentFixture<TankEdit>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TankEdit]
    })
    .compileComponents();

    fixture = TestBed.createComponent(TankEdit);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
