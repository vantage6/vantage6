import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AlgorithmListComponent } from './algorithm-list.component';

describe('AlgorithmListComponent', () => {
  let component: AlgorithmListComponent;
  let fixture: ComponentFixture<AlgorithmListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AlgorithmListComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(AlgorithmListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
