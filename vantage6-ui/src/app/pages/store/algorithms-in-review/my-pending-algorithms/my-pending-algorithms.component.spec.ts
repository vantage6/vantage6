import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MyPendingAlgorithmsComponent } from './my-pending-algorithms.component';

describe('MyPendingAlgorithmsComponent', () => {
  let component: MyPendingAlgorithmsComponent;
  let fixture: ComponentFixture<MyPendingAlgorithmsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [MyPendingAlgorithmsComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(MyPendingAlgorithmsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
