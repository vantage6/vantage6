import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AlgorithmReadPublicComponent } from './algorithm-read-public.component';

describe('ReadPublicComponent', () => {
  let component: AlgorithmReadPublicComponent;
  let fixture: ComponentFixture<AlgorithmReadPublicComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [AlgorithmReadPublicComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AlgorithmReadPublicComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
