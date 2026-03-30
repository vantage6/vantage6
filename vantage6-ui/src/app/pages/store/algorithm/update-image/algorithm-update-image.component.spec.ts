import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AlgorithmUpdateImageComponent } from './algorithm-update-image.component';

describe('AlgorithmUpdateImageComponent', () => {
  let component: AlgorithmUpdateImageComponent;
  let fixture: ComponentFixture<AlgorithmUpdateImageComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [AlgorithmUpdateImageComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AlgorithmUpdateImageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
