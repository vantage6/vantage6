import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CollaboartionCreateComponent } from './collaboration-create.component';

describe('CollaboartionCreateComponent', () => {
  let component: CollaboartionCreateComponent;
  let fixture: ComponentFixture<CollaboartionCreateComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [CollaboartionCreateComponent]
    });
    fixture = TestBed.createComponent(CollaboartionCreateComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
