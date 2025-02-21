import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AlgorithmFormComponent } from './algorithm-form.component';

describe('AlgorithmFormComponent', () => {
  let component: AlgorithmFormComponent;
  let fixture: ComponentFixture<AlgorithmFormComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AlgorithmFormComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(AlgorithmFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
