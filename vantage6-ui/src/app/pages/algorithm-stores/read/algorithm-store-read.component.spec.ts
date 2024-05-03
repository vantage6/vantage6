import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AlgorithmStoreReadComponent } from './algorithm-store-read.component';

describe('AlgorithmStoreReadComponent', () => {
  let component: AlgorithmStoreReadComponent;
  let fixture: ComponentFixture<AlgorithmStoreReadComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [AlgorithmStoreReadComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(AlgorithmStoreReadComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
