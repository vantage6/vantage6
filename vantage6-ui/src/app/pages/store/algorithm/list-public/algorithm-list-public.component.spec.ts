import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AlgorithmListPublicComponent } from './algorithm-list-public.component';

describe('AlgorithmListComponent', () => {
  let component: AlgorithmListPublicComponent;
  let fixture: ComponentFixture<AlgorithmListPublicComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AlgorithmListPublicComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(AlgorithmListPublicComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
