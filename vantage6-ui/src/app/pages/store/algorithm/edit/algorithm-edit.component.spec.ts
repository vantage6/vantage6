import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AlgorithmEditComponent } from './algorithm-edit.component';

describe('AlgorithmEditComponent', () => {
  let component: AlgorithmEditComponent;
  let fixture: ComponentFixture<AlgorithmEditComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AlgorithmEditComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(AlgorithmEditComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
