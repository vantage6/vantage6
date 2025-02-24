import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BaseEditComponent } from './base-edit.component';

describe('BaseEditComponent', () => {
  let component: BaseEditComponent;
  let fixture: ComponentFixture<BaseEditComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BaseEditComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(BaseEditComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
