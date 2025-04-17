import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AlgorithmTableComponent } from './algorithm-table.component';

describe('AlgorithmTableComponent', () => {
  let component: AlgorithmTableComponent;
  let fixture: ComponentFixture<AlgorithmTableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [AlgorithmTableComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AlgorithmTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
