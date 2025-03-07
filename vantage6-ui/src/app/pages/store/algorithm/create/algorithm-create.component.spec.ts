import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AlgorithmCreateComponent } from './algorithm-create.component';

describe('AlgorithmCreateComponent', () => {
  let component: AlgorithmCreateComponent;
  let fixture: ComponentFixture<AlgorithmCreateComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AlgorithmCreateComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(AlgorithmCreateComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
