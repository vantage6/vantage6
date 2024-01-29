import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AlgorithmStoreFormComponent } from './algorithm-store-form.component';

describe('AlgorithmStoreFormComponent', () => {
  let component: AlgorithmStoreFormComponent;
  let fixture: ComponentFixture<AlgorithmStoreFormComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [AlgorithmStoreFormComponent]
    });
    fixture = TestBed.createComponent(AlgorithmStoreFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
