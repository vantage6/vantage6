import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BaseCreateComponent } from './base-create.component';

describe('BaseCreateComponent', () => {
  let component: BaseCreateComponent;
  let fixture: ComponentFixture<BaseCreateComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BaseCreateComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(BaseCreateComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
