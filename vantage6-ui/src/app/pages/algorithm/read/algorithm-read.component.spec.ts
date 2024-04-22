import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AlgorithmReadComponent } from './algorithm-read.component';

describe('AlgorithmReadComponent', () => {
  let component: AlgorithmReadComponent;
  let fixture: ComponentFixture<AlgorithmReadComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AlgorithmReadComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(AlgorithmReadComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
