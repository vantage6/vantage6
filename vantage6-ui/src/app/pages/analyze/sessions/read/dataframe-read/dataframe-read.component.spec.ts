import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DataframeReadComponent } from './dataframe-read.component';

describe('DataframeReadComponent', () => {
  let component: DataframeReadComponent;
  let fixture: ComponentFixture<DataframeReadComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [DataframeReadComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(DataframeReadComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
