import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BaseReadComponent } from './base-read.component';

describe('BaseReadComponent', () => {
  let component: BaseReadComponent;
  let fixture: ComponentFixture<BaseReadComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [BaseReadComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(BaseReadComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
